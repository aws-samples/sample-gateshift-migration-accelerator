"""Unit tests for API authentication and ownership enforcement."""

import json
import sys
from unittest.mock import MagicMock

import pytest

# boto3 is not needed for these tests; stub it before importing handlers.
sys.modules["boto3"] = MagicMock()

from api import helpers  # noqa: E402
from api.helpers import (  # noqa: E402
    ForbiddenError,
    UnauthorizedError,
    get_caller,
    load_owned_migration,
    cors_headers,
)


def make_event(sub=None, token_use="id", email="user@example.com", **kwargs):
    """Build an API Gateway proxy event with optional Cognito claims."""
    claims = {}
    if sub:
        claims["sub"] = sub
        claims["email"] = email
        if token_use:
            claims["token_use"] = token_use

    event = {"requestContext": {"authorizer": {"claims": claims} if claims else {}}}
    event.update(kwargs)
    return event


class TestGetCaller:
    """The caller identity must come from verified authorizer claims."""

    def test_valid_id_token_returns_caller(self):
        caller = get_caller(make_event(sub="user-123"))
        assert caller["sub"] == "user-123"
        assert caller["email"] == "user@example.com"

    def test_missing_authorizer_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            get_caller({"requestContext": {}})

    def test_missing_claims_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            get_caller(make_event())

    def test_missing_sub_raises_unauthorized(self):
        event = {"requestContext": {"authorizer": {"claims": {"email": "a@b.c"}}}}
        with pytest.raises(UnauthorizedError):
            get_caller(event)

    def test_access_token_is_rejected(self):
        """Only ID tokens are accepted; access tokens must fail closed."""
        with pytest.raises(UnauthorizedError, match="ID token"):
            get_caller(make_event(sub="user-123", token_use="access"))

    def test_absent_token_use_is_tolerated(self):
        caller = get_caller(make_event(sub="user-123", token_use=None))
        assert caller["sub"] == "user-123"

    def test_empty_event_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            get_caller({})


class TestLoadOwnedMigration:
    """Ownership must be enforced on every single-record read."""

    def setup_method(self):
        helpers.table = MagicMock()

    def test_owner_can_load(self):
        helpers.table.get_item.return_value = {
            "Item": {"migration_id": "m1", "owner_sub": "user-123"}
        }
        item = load_owned_migration("m1", {"sub": "user-123"})
        assert item["migration_id"] == "m1"

    def test_non_owner_raises_forbidden(self):
        helpers.table.get_item.return_value = {
            "Item": {"migration_id": "m1", "owner_sub": "someone-else"}
        }
        with pytest.raises(ForbiddenError):
            load_owned_migration("m1", {"sub": "user-123"})

    def test_missing_record_raises_keyerror(self):
        helpers.table.get_item.return_value = {}
        with pytest.raises(KeyError):
            load_owned_migration("nope", {"sub": "user-123"})

    def test_record_without_owner_raises_forbidden(self):
        """Legacy rows with no owner must not be readable by anyone."""
        helpers.table.get_item.return_value = {"Item": {"migration_id": "m1"}}
        with pytest.raises(ForbiddenError):
            load_owned_migration("m1", {"sub": "user-123"})


class TestCorsHeaders:
    """Responses must not use a wildcard origin."""

    def test_origin_is_not_wildcard(self):
        assert cors_headers()["Access-Control-Allow-Origin"] != "*"

    def test_includes_hardening_headers(self):
        headers = cors_headers()
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "Strict-Transport-Security" in headers
        assert headers["Cache-Control"] == "no-store"


class TestPresignUploadValidation:
    """Filename validation blocks traversal and unexpected file types."""

    def setup_method(self):
        from api import presign_upload

        self.mod = presign_upload

    @pytest.mark.parametrize(
        "name",
        ["kong.yaml", "kong.yml", "my-config.yaml", "config_v2.yml", "a.yaml"],
    )
    def test_accepts_valid_yaml_names(self, name):
        assert self.mod.SAFE_FILENAME.match(name)

    @pytest.mark.parametrize(
        "name",
        [
            "../../etc/passwd.yaml",
            "sub/dir/config.yaml",
            "config.json",
            "config.yaml.exe",
            "config",
            "",
            "conf ig.yaml",
            "config.yaml\n",
            "a" * 200 + ".yaml",
        ],
    )
    def test_rejects_unsafe_names(self, name):
        assert not self.mod.SAFE_FILENAME.match(name)

    def test_unauthenticated_request_returns_401(self):
        result = self.mod.handler({"requestContext": {}}, None)
        assert result["statusCode"] == 401

    def test_invalid_filename_returns_400(self):
        event = make_event(sub="user-1", body=json.dumps({"fileName": "../evil.yaml"}))
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 400


class TestCreateMigrationOwnership:
    """A caller may only start a migration from their own upload prefix."""

    def setup_method(self):
        from api import create_migration

        self.mod = create_migration
        self.mod.table = MagicMock()
        self.mod.sfn = MagicMock()

    def test_unauthenticated_returns_401(self):
        result = self.mod.handler({"requestContext": {}}, None)
        assert result["statusCode"] == 401

    def test_missing_key_returns_400(self):
        event = make_event(sub="user-1", body=json.dumps({}))
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 400

    def test_foreign_prefix_returns_403(self):
        """Pointing at another user's uploaded object must be refused."""
        event = make_event(
            sub="user-1",
            body=json.dumps({"configS3Key": "input/user-2/abc/kong.yaml"}),
        )
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 403

    def test_traversal_in_key_returns_403(self):
        event = make_event(
            sub="user-1",
            body=json.dumps({"configS3Key": "input/user-1/../user-2/kong.yaml"}),
        )
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 403

    def test_unsupported_source_type_returns_400(self):
        event = make_event(
            sub="user-1",
            body=json.dumps(
                {"sourceType": "apigee", "configS3Key": "input/user-1/a/kong.yaml"}
            ),
        )
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 400

    def test_own_prefix_succeeds_and_records_owner(self):
        event = make_event(
            sub="user-1",
            body=json.dumps({"configS3Key": "input/user-1/abc/kong.yaml"}),
        )
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 201

        item = self.mod.table.put_item.call_args.kwargs["Item"]
        assert item["owner_sub"] == "user-1"
        assert item["status"] == "PENDING"

    def test_pipeline_failure_does_not_leak_internals(self):
        self.mod.sfn.start_execution.side_effect = RuntimeError(
            "arn:aws:states:us-east-1:123456789012:stateMachine:secret"
        )
        event = make_event(
            sub="user-1",
            body=json.dumps({"configS3Key": "input/user-1/abc/kong.yaml"}),
        )
        result = self.mod.handler(event, None)
        assert result["statusCode"] == 500
        assert "arn:aws" not in result["body"]


class TestPresignDownloadAllowList:
    """Artifact names are restricted to a fixed allow-list."""

    def setup_method(self):
        from api import presign_download

        self.mod = presign_download

    def test_unauthenticated_returns_401(self):
        result = self.mod.handler({"requestContext": {}}, None)
        assert result["statusCode"] == 401

    def test_allow_list_has_no_traversal_values(self):
        for path in self.mod.ARTIFACT_MAP.values():
            assert ".." not in path
            assert not path.startswith("/")

    def test_unknown_artifact_is_not_in_map(self):
        assert self.mod.ARTIFACT_MAP.get("../../secrets") is None
