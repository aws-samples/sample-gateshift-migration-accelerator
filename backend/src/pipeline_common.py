"""Shared helpers for the Step Functions pipeline Lambda functions.

Centralises DynamoDB status updates so that a crash in any stage still leaves
the migration record in a terminal FAILED state instead of a stuck in-progress
status that the frontend would poll forever.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import boto3

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(os.environ.get("MIGRATIONS_TABLE", "GateShiftMigrations"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_status(migration_id: str, status: str) -> None:
    """Set the migration status (in-progress phases)."""
    _table.update_item(
        Key={"migration_id": migration_id},
        UpdateExpression="SET #s = :status, updated_at = :ts",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": status, ":ts": _now()},
    )


def mark_failed(migration_id: str, message: str = "Migration pipeline failed") -> None:
    """
    Move the migration to FAILED with a short, non-sensitive error message.

    Best-effort: never raises, so it can be called from an except block without
    masking the original error.
    """
    try:
        _table.update_item(
            Key={"migration_id": migration_id},
            UpdateExpression=(
                "SET #s = :status, error_message = :err, updated_at = :ts"
            ),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":err": str(message)[:500],
                ":ts": _now(),
            },
        )
    except Exception as exc:  # pragma: no cover - logging only
        print(f"Could not mark migration {migration_id} FAILED: {exc}")
