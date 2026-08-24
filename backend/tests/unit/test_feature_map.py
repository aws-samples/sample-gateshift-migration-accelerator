"""Unit tests for the deterministic feature mapping engine."""

import pytest

from analyzer.feature_map import get_mapping, get_all_mappable_plugins, KONG_TO_AWS_MAP


class TestGetMapping:
    """Tests for the get_mapping function."""

    def test_known_plugin_returns_mapping(self):
        result = get_mapping("key-auth")
        assert result is not None
        assert "aws_service" in result
        assert "mapping_type" in result

    def test_unknown_plugin_returns_none(self):
        result = get_mapping("nonexistent-plugin")
        assert result is None

    def test_key_auth_mapping_is_direct(self):
        result = get_mapping("key-auth")
        assert result["mapping_type"] == "direct"

    def test_key_auth_requires_rest_api(self):
        result = get_mapping("key-auth")
        assert result["api_type_required"] == "REST"

    def test_jwt_mapping_is_lambda(self):
        result = get_mapping("jwt")
        assert result["mapping_type"] == "lambda"

    def test_jwt_works_with_any_api_type(self):
        result = get_mapping("jwt")
        assert result["api_type_required"] is None

    def test_cors_mapping_is_direct(self):
        result = get_mapping("cors")
        assert result["mapping_type"] == "direct"
        assert result["api_type_required"] is None

    def test_rate_limiting_mapping(self):
        result = get_mapping("rate-limiting")
        assert result["mapping_type"] == "direct"
        assert result["api_type_required"] == "REST"
        assert "Usage Plan" in result["aws_service"]

    def test_bot_detection_is_alternative(self):
        result = get_mapping("bot-detection")
        assert result["mapping_type"] == "alternative"
        assert "WAF" in result["aws_service"]

    def test_request_transformer_is_lambda(self):
        result = get_mapping("request-transformer")
        assert result["mapping_type"] == "lambda"
        assert "VTL" in result["aws_service"] or "Lambda" in result["aws_service"]

    def test_proxy_cache_is_direct_rest_only(self):
        result = get_mapping("proxy-cache")
        assert result["mapping_type"] == "direct"
        assert result["api_type_required"] == "REST"

    def test_http_log_is_alternative(self):
        result = get_mapping("http-log")
        assert result["mapping_type"] == "alternative"
        assert "Firehose" in result["aws_service"]

    def test_opentelemetry_is_direct(self):
        result = get_mapping("opentelemetry")
        assert result["mapping_type"] == "direct"
        assert "X-Ray" in result["aws_service"]

    def test_session_is_lambda(self):
        result = get_mapping("session")
        assert result["mapping_type"] == "lambda"
        assert "DynamoDB" in result["aws_service"]

    def test_mtls_is_direct(self):
        result = get_mapping("mtls-auth")
        assert result["mapping_type"] == "direct"
        assert "Mutual TLS" in result["aws_service"]


class TestGetAllMappablePlugins:
    """Tests for the get_all_mappable_plugins function."""

    def test_returns_list(self):
        result = get_all_mappable_plugins()
        assert isinstance(result, list)

    def test_contains_common_plugins(self):
        plugins = get_all_mappable_plugins()
        expected = ["key-auth", "jwt", "rate-limiting", "cors", "ip-restriction"]
        for p in expected:
            assert p in plugins

    def test_returns_at_least_20_plugins(self):
        plugins = get_all_mappable_plugins()
        assert len(plugins) >= 20

    def test_all_plugins_have_valid_mapping(self):
        for plugin_name in get_all_mappable_plugins():
            mapping = get_mapping(plugin_name)
            assert mapping is not None
            assert mapping["mapping_type"] in ("direct", "lambda", "alternative", "gap")


class TestMappingStructure:
    """Tests for the structure of each mapping entry."""

    def test_all_mappings_have_required_keys(self):
        required_keys = {"aws_service", "mapping_type", "api_type_required", "implementation_notes"}
        for plugin_name, mapping in KONG_TO_AWS_MAP.items():
            missing = required_keys - set(mapping.keys())
            assert not missing, f"{plugin_name} is missing keys: {missing}"

    def test_all_mapping_types_are_valid(self):
        valid_types = {"direct", "lambda", "alternative", "gap"}
        for plugin_name, mapping in KONG_TO_AWS_MAP.items():
            assert mapping["mapping_type"] in valid_types, (
                f"{plugin_name} has invalid mapping_type: {mapping['mapping_type']}"
            )

    def test_api_type_required_is_valid(self):
        valid_values = {"REST", None}
        for plugin_name, mapping in KONG_TO_AWS_MAP.items():
            assert mapping["api_type_required"] in valid_values, (
                f"{plugin_name} has invalid api_type_required: {mapping['api_type_required']}"
            )

    def test_implementation_notes_not_empty(self):
        for plugin_name, mapping in KONG_TO_AWS_MAP.items():
            assert mapping["implementation_notes"].strip(), (
                f"{plugin_name} has empty implementation_notes"
            )

    def test_aws_service_not_empty(self):
        for plugin_name, mapping in KONG_TO_AWS_MAP.items():
            assert mapping["aws_service"].strip(), (
                f"{plugin_name} has empty aws_service"
            )
