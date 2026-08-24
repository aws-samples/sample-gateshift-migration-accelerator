"""Get validation report for a migration."""

from __future__ import annotations

import json

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

FINISHED_STATUSES = {"COMPLETE", "NEEDS_REVIEW"}


def handler(event: dict, context) -> dict:
    """GET /migrations/{id}/report — Get full validation report."""
    try:
        caller = get_caller(event)
    except UnauthorizedError as exc:
        return error_response(401, str(exc))

    migration_id = (event.get("pathParameters") or {}).get("id")
    if not migration_id:
        return error_response(400, "Migration ID is required")

    try:
        item = load_owned_migration(migration_id, caller)
    except KeyError:
        return error_response(404, "Migration not found")
    except ForbiddenError:
        return error_response(404, "Migration not found")

    if item.get("status") not in FINISHED_STATUSES:
        return error_response(
            409, f"Migration is still in progress (status: {item.get('status')})"
        )

    try:
        report_obj = s3.get_object(
            Bucket=BUCKET,
            Key=f"migrations/{migration_id}/output/validation-report.json",
        )
        report = json.loads(report_obj["Body"].read())
    except s3.exceptions.NoSuchKey:
        return error_response(404, "Validation report not found")
    except Exception as exc:
        print(f"Failed to read report for {migration_id}: {exc}")
        return error_response(500, "Could not retrieve validation report")

    return response(200, report)
