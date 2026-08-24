"""Create and start a new migration."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import boto3

from .helpers import (
    BUCKET,
    UnauthorizedError,
    error_response,
    get_caller,
    response,
    table,
)

sfn = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")

SUPPORTED_SOURCE_TYPES = {"kong"}


def handler(event: dict, context) -> dict:
    """POST /migrations — Create and start a new migration pipeline."""
    try:
        caller = get_caller(event)
    except UnauthorizedError as exc:
        return error_response(401, str(exc))

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response(400, "Invalid JSON body")

    source_type = body.get("sourceType", "kong")
    config_s3_key = body.get("configS3Key")
    file_name = body.get("fileName", "config.yaml")

    if not config_s3_key or not isinstance(config_s3_key, str):
        return error_response(400, "configS3Key is required")

    if source_type not in SUPPORTED_SOURCE_TYPES:
        return error_response(
            400, f"Unsupported source type: {source_type}. Only 'kong' is supported."
        )

    # The caller may only start a migration from a key inside their own prefix.
    # Without this check a user could point the pipeline at another user's upload.
    expected_prefix = f"input/{caller['sub']}/"
    if not config_s3_key.startswith(expected_prefix) or ".." in config_s3_key:
        return error_response(403, "configS3Key does not belong to the caller")

    migration_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    table.put_item(
        Item={
            "migration_id": migration_id,
            "owner_sub": caller["sub"],
            "owner_email": caller["email"],
            "source_type": source_type,
            "config_s3_key": config_s3_key,
            "file_name": file_name,
            "status": "PENDING",
            "created_at": now,
            "updated_at": now,
        }
    )

    sfn_input = {
        "migration_id": migration_id,
        "source_type": source_type,
        "config_s3_key": config_s3_key,
        "bucket": BUCKET,
    }

    try:
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=migration_id,
            input=json.dumps(sfn_input),
        )
    except Exception as exc:
        table.update_item(
            Key={"migration_id": migration_id},
            UpdateExpression="SET #s = :status, error_message = :err, updated_at = :ts",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":err": "Failed to start migration pipeline",
                ":ts": datetime.now(timezone.utc).isoformat(),
            },
        )
        # Log detail server-side; do not leak internals to the client.
        print(f"start_execution failed for {migration_id}: {exc}")
        return error_response(500, "Failed to start migration pipeline")

    return response(201, {"migrationId": migration_id})
