"""Lambda handler for the Parse phase of GateShift pipeline."""

from __future__ import annotations

import json
import os

import boto3

from pipeline_common import mark_failed

from .kong_parser import KongParser
from .models import NormalizedConfig

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("MIGRATIONS_TABLE", "GateShiftMigrations"))


def handler(event: dict, context) -> dict:
    """
    Parse source platform configuration into normalized intermediate format.

    Input event:
        - migration_id: str
        - source_type: str (kong | apigee | ibm)
        - config_s3_key: str
        - bucket: str
    """
    migration_id = event["migration_id"]

    try:
        return _run(event, migration_id)
    except Exception as exc:
        mark_failed(migration_id, "Parse stage failed")
        print(f"Parser failed for {migration_id}: {exc}")
        raise


def _run(event: dict, migration_id: str) -> dict:
    source_type = event["source_type"]
    config_key = event["config_s3_key"]
    bucket = event["bucket"]

    # Update status
    _update_status(migration_id, "PARSING")

    # Download source config from S3
    response = s3.get_object(Bucket=bucket, Key=config_key)
    raw_config = response["Body"].read().decode("utf-8")

    # Parse based on source type
    if source_type == "kong":
        parser = KongParser()
        normalized: NormalizedConfig = parser.parse(raw_config)
    else:
        raise ValueError(f"Unsupported source type: {source_type}. Only 'kong' is supported in v1.")

    # Serialize and store normalized config
    normalized_json = normalized.model_dump()

    s3.put_object(
        Bucket=bucket,
        Key=f"migrations/{migration_id}/normalized.json",
        Body=json.dumps(normalized_json, indent=2),
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "migration_id": migration_id,
        "bucket": bucket,
        "source_type": source_type,
        "api_count": len(normalized.apis),
        "route_count": sum(len(api.routes) for api in normalized.apis),
        "plugin_count": sum(len(api.plugins) for api in normalized.apis) + len(normalized.global_plugins),
    }


def _update_status(migration_id: str, status: str) -> None:
    """Update migration status in DynamoDB."""
    from datetime import datetime, timezone

    table.update_item(
        Key={"migration_id": migration_id},
        UpdateExpression="SET #s = :status, updated_at = :ts",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": status,
            ":ts": datetime.now(timezone.utc).isoformat(),
        },
    )
