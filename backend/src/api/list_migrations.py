"""List the caller's migrations."""

from __future__ import annotations

from boto3.dynamodb.conditions import Key

from .helpers import UnauthorizedError, error_response, get_caller, response, table

# Fields safe to return to the browser. owner_sub and config_s3_key stay internal.
PROJECTION = (
    "migration_id, source_type, #s, created_at, updated_at, "
    "file_name, confidence_score, target_api_type"
)


def handler(event: dict, context) -> dict:
    """GET /migrations — List migrations owned by the caller."""
    try:
        caller = get_caller(event)
    except UnauthorizedError as exc:
        return error_response(401, str(exc))

    # Query the owner index so a caller can never read another user's rows.
    result = table.query(
        IndexName="owner-index",
        KeyConditionExpression=Key("owner_sub").eq(caller["sub"]),
        ProjectionExpression=PROJECTION,
        ExpressionAttributeNames={"#s": "status"},
        ScanIndexForward=False,  # newest first
        Limit=50,
    )

    return response(200, {"migrations": result.get("Items", [])})
