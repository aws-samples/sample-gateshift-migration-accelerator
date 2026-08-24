"""Presign S3 download URL for migration artifacts."""

from __future__ import annotations

from .helpers import (
    BUCKET,
    ForbiddenError,
    UnauthorizedError,
    error_response,
    get_caller,
    load_owned_migration,
    response,
    s3,
)

# Allow-list of artifacts. Prevents the path segment from being used to reach
# arbitrary keys such as another migration's files.
ARTIFACT_MAP = {
    "template": "output/template.yaml",
    "openapi": "output/openapi.yaml",
    "report": "output/validation-report.json",
    "cfn-lint": "output/cfn-lint.json",
    "migration-report": "output/migration-report.md",
    "authorizer": "output/authorizer/index.py",
    "normalized": "normalized.json",
    "plan": "migration_plan.json",
}


def handler(event: dict, context) -> dict:
    """GET /migrations/{id}/download/{artifact} — Get presigned download URL."""
    try:
        caller = get_caller(event)
    except UnauthorizedError as exc:
        return error_response(401, str(exc))

    path_params = event.get("pathParameters") or {}
    migration_id = path_params.get("id")
    artifact = path_params.get("artifact")

    if not migration_id:
        return error_response(400, "Migration ID is required")
    if not artifact:
        return error_response(400, "Artifact name is required")

    try:
        load_owned_migration(migration_id, caller)
    except KeyError:
        return error_response(404, "Migration not found")
    except ForbiddenError:
        return error_response(404, "Migration not found")

    artifact_path = ARTIFACT_MAP.get(artifact)
    if not artifact_path:
        return error_response(
            400, f"Unknown artifact. Available: {sorted(ARTIFACT_MAP)}"
        )

    s3_key = f"migrations/{migration_id}/{artifact_path}"

    try:
        s3.head_object(Bucket=BUCKET, Key=s3_key)
    except Exception:
        return error_response(404, "Artifact not found for this migration")

    download_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": s3_key},
        ExpiresIn=300,
    )

    return response(200, {"url": download_url, "artifact": artifact})
