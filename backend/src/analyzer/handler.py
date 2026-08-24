"""Lambda handler for the Analyze phase of GateShift pipeline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import boto3

from pipeline_common import mark_failed

from .feature_map import get_mapping
from .prompts import ANALYSIS_SYSTEM_PROMPT, MIGRATION_PLAN_TOOL, build_analysis_prompt

s3 = boto3.client("s3")
bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("BEDROCK_REGION", "us-east-1"),
)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("MIGRATIONS_TABLE", "GateShiftMigrations"))


def handler(event: dict, context) -> dict:
    """
    Analyze normalized config using deterministic mapping + Bedrock.

    Input event (from Step Functions):
        - migration_id: str
        - bucket: str
        - source_type: str
        - (other fields from parse phase)
    """
    migration_id = event["migration_id"]

    try:
        return _run(event, migration_id)
    except Exception as exc:
        mark_failed(migration_id, "Analysis stage failed")
        print(f"Analyzer failed for {migration_id}: {exc}")
        raise


def _run(event: dict, migration_id: str) -> dict:
    bucket = event["bucket"]

    _update_status(migration_id, "ANALYZING")

    # Load normalized config from S3
    normalized = json.loads(
        s3.get_object(
            Bucket=bucket,
            Key=f"migrations/{migration_id}/normalized.json",
        )["Body"].read()
    )

    # Phase 1: Deterministic mapping for known plugins
    deterministic_mappings = _compute_deterministic_mappings(normalized)

    # Phase 2: Call Bedrock for full analysis (handles edge cases, interactions, recommendations)
    migration_plan = _analyze_with_bedrock(normalized, deterministic_mappings)

    # Store migration plan
    s3.put_object(
        Bucket=bucket,
        Key=f"migrations/{migration_id}/migration_plan.json",
        Body=json.dumps(migration_plan, indent=2),
        ContentType="application/json",
    )

    summary = migration_plan.get("summary", {})

    return {
        "statusCode": 200,
        "migration_id": migration_id,
        "bucket": bucket,
        "target_api_type": migration_plan.get("target_api_type", "REST"),
        "direct_mappings": summary.get("direct_count", 0),
        "lambda_required": summary.get("lambda_count", 0),
        "gaps_detected": summary.get("gap_count", 0),
        "estimated_effort_hours": summary.get("estimated_effort_hours", 0),
    }


def _compute_deterministic_mappings(normalized: dict) -> list[dict]:
    """Pre-compute mappings for known plugins without needing Bedrock."""
    mappings = []

    all_plugins = normalized.get("global_plugins", [])
    for api in normalized.get("apis", []):
        all_plugins.extend(api.get("plugins", []))

    seen_plugins = set()
    for plugin in all_plugins:
        plugin_name = plugin.get("source_plugin_name", plugin.get("name", ""))
        if plugin_name in seen_plugins:
            continue
        seen_plugins.add(plugin_name)

        mapping = get_mapping(plugin_name)
        if mapping:
            mappings.append(
                {
                    "source_plugin_name": plugin_name,
                    "aws_service": mapping["aws_service"],
                    "mapping_type": mapping["mapping_type"],
                    "api_type_required": mapping.get("api_type_required"),
                    "implementation_notes": mapping["implementation_notes"],
                    "plugin_config": plugin.get("config", {}),
                }
            )

    return mappings


def _analyze_with_bedrock(normalized: dict, deterministic_mappings: list[dict]) -> dict:
    """Call Bedrock to produce full migration plan."""
    model_id = os.environ.get(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )

    prompt = build_analysis_prompt(normalized, deterministic_mappings)

    response = bedrock.converse(
        modelId=model_id,
        system=[{"text": ANALYSIS_SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.1},
        toolConfig={"tools": [MIGRATION_PLAN_TOOL]},
    )

    # Extract tool use response
    return _extract_tool_use_response(response)


def _extract_tool_use_response(response: dict) -> dict:
    """Extract structured data from Bedrock tool use response."""
    output = response.get("output", {})
    message = output.get("message", {})

    for content_block in message.get("content", []):
        if content_block.get("toolUse"):
            return content_block["toolUse"].get("input", {})

    # Fallback: if no tool use, return a basic plan
    return {
        "target_api_type": "REST",
        "target_api_type_reasoning": "Default recommendation",
        "apis": [],
        "summary": {
            "direct_count": 0,
            "lambda_count": 0,
            "alternative_count": 0,
            "gap_count": 0,
            "estimated_effort_hours": 0,
        },
        "warnings": ["Bedrock did not return structured output. Manual review required."],
    }


def _update_status(migration_id: str, status: str) -> None:
    """Update migration status in DynamoDB."""
    table.update_item(
        Key={"migration_id": migration_id},
        UpdateExpression="SET #s = :status, updated_at = :ts",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": status,
            ":ts": datetime.now(timezone.utc).isoformat(),
        },
    )
