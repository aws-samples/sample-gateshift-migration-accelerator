"""Presign S3 upload URL for config file uploads."""

from __future__ import annotations

import json
import re
import uuid

from .helpers import (
    BUCKET,
    UnauthorizedError,
    error_response,
    get_caller,
    response,
    s3,
)

# Reject anything that is not a plain YAML filename. This blocks path
# traversal and control characters from reaching the S3 key.
# \Z rather than $ so a trailing newline cannot slip through.
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]{1,120}\.(ya?ml)\Z")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def handler(event: dict, context) -> dict:
    """POST /uploads/presign — Generate a presigned URL for S3 upload."""
    try:
        caller = get_caller(event)
    except UnauthorizedError as exc:
        return error_response(401, str(exc))

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return error_response(400, "Invalid JSON body")

    file_name = body.get("fileName", "config.yaml")

    if not isinstance(file_name, str) or not SAFE_FILENAME.match(file_name):
        return error_response(
            400,
            "fileName must be a simple .yaml or .yml name without path separators",
        )

    # Namespace uploads per caller so one user cannot overwrite another's input.
    upload_id = uuid.uuid4().hex
    s3_key = f"input/{caller['sub']}/{upload_id}/{file_name}"

    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": s3_key,
            "ContentType": "application/x-yaml",
        },
        ExpiresIn=300,
    )

    return response(
        200,
        {
            "uploadUrl": upload_url,
            "s3Key": s3_key,
            "maxBytes": MAX_UPLOAD_BYTES,
        },
    )
