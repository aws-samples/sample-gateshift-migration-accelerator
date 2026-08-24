"""Shared helpers for API Lambda handlers."""

from __future__ import annotations

import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("MIGRATIONS_TABLE", "GateShiftMigrations"))
s3 = boto3.client("s3")

BUCKET = os.environ.get("ARTIFACTS_BUCKET", "gateshift-artifacts")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:3000")


class UnauthorizedError(Exception):
    """Raised when the caller identity cannot be established."""


class ForbiddenError(Exception):
    """Raised when the caller is authenticated but not the resource owner."""


def cors_headers() -> dict:
    """CORS headers pinned to the configured origin (never a wildcard)."""
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Vary": "Origin",
        # Defensive response headers.
        "Cache-Control": "no-store",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "Content-Type": "application/json",
    }


def response(status_code: int, body: dict) -> dict:
    """Build API Gateway Lambda proxy response."""
    return {
        "statusCode": status_code,
        "headers": cors_headers(),
        "body": json.dumps(body, default=str),
    }


def error_response(status_code: int, message: str) -> dict:
    """Build error response."""
    return response(status_code, {"error": message})


def get_caller(event: dict) -> dict:
    """
    Extract the authenticated caller from the API Gateway Cognito authorizer.

    API Gateway rejects unauthenticated requests before invoking the function,
    so claims are expected to be present. We still validate rather than trust,
    so a misconfigured authorizer fails closed instead of open.
    """
    claims = (
        event.get("requestContext", {}).get("authorizer", {}).get("claims") or {}
    )

    subject = claims.get("sub")
    if not subject:
        raise UnauthorizedError("Missing caller identity")

    # Reject access tokens: only ID tokens carry the audience we expect and
    # API Gateway's Cognito authorizer accepts both by default.
    token_use = claims.get("token_use")
    if token_use and token_use != "id":
        raise UnauthorizedError("An ID token is required")

    return {
        "sub": subject,
        "email": claims.get("email", ""),
    }


def load_owned_migration(migration_id: str, caller: dict) -> dict:
    """
    Fetch a migration and verify the caller owns it.

    Raises ForbiddenError when the record belongs to another user so that
    knowing an ID is not sufficient to read someone else's data.
    """
    result = table.get_item(Key={"migration_id": migration_id})
    item = result.get("Item")

    if not item:
        raise KeyError(migration_id)

    if item.get("owner_sub") != caller["sub"]:
        raise ForbiddenError("Caller does not own this migration")

    return item
