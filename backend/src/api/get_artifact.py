"""Return artifact text content for in-app viewing (and client-side download).

Serving content through the authenticated API keeps ownership enforcement and
avoids handing raw S3 URLs to the browser or relaxing S3 CORS.
"""

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

# artifact key -> (s3 relative path, download filename)
ARTIFACT_MAP = {
    "template": ("output/template.yaml", "template.yaml"),
    "openapi": ("output/openapi.yaml", "openapi.yaml"),
    "report": ("output/validation-report.json", "validation-report.json"),
    "cfn-lint": ("output/cfn-lint.json", "cfn-lint.json"),
    "migration-report": ("output/migration-report.md", "migration-report.md"),
    "authorizer": ("output/authorizer/index.py", "index.py"),
    "normalized": ("normalized.json", "normalized.json"),
    "plan": ("migration_plan.json", "migration_plan.json"),
}

# Artifacts are small; cap defensively so a huge object cannot be pulled into memory.
MAX_BYTES = 1_000_000


def handler(event: dict, context) -> dict:
    """GET /migrations/{id}/artifact/{artifact} — return artifact text content."""
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

    entry = ARTIFACT_MAP.get(artifact)
    if not entry:
        return error_response(400, f"Unknown artifact. Available: {sorted(ARTIFACT_MAP)}")

    rel_path, filename = entry
    s3_key = f"migrations/{migration_id}/{rel_path}"

    try:
        obj = s3.get_object(Bucket=BUCKET, Key=s3_key)
    except Exception:
        return error_response(404, "Artifact not found for this migration")

    body = obj["Body"].read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        return error_response(413, "Artifact too large to preview")

    try:
        content = body.decode("utf-8")
    except UnicodeDecodeError:
        return error_response(415, "Artifact is not previewable text")

    return response(200, {"artifact": artifact, "filename": filename, "content": content})
