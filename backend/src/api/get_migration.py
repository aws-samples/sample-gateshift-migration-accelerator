"""Get single migration details."""

from __future__ import annotations

from .helpers import (
    ForbiddenError,
    UnauthorizedError,
    error_response,
    get_caller,
    load_owned_migration,
    response,
)

# Internal fields that must not reach the browser.
INTERNAL_FIELDS = {"owner_sub", "owner_email", "config_s3_key"}


def handler(event: dict, context) -> dict:
    """GET /migrations/{id} — Get migration status and details."""
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
        # Same body as a miss so ownership cannot be probed.
        return error_response(404, "Migration not found")

    public = {k: v for k, v in item.items() if k not in INTERNAL_FIELDS}
    return response(200, public)
