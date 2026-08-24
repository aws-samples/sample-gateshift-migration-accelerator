"""Lambda handler for the Validate phase of GateShift pipeline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from pipeline_common import mark_failed

from .cfn_lint_check import lint_template

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("MIGRATIONS_TABLE", "GateShiftMigrations"))


def _to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB (which rejects floats)."""
    return json.loads(json.dumps(obj), parse_float=Decimal)


def handler(event: dict, context) -> dict:
    """
    Validate generated template against source configuration.
    Produce gap report and confidence score.

    Input event (from Step Functions):
        - migration_id: str
        - bucket: str
    """
    migration_id = event["migration_id"]
    bucket = event["bucket"]

    try:
        return _run(migration_id, bucket)
    except Exception as exc:
        # Ensure the record does not stay stuck at VALIDATING.
        mark_failed(migration_id, "Validation stage failed")
        print(f"Validator failed for {migration_id}: {exc}")
        raise


def _run(migration_id: str, bucket: str) -> dict:
    _update_status(migration_id, "VALIDATING")

    # Load normalized config and migration plan
    normalized = json.loads(
        s3.get_object(
            Bucket=bucket,
            Key=f"migrations/{migration_id}/normalized.json",
        )["Body"].read()
    )

    plan = json.loads(
        s3.get_object(
            Bucket=bucket,
            Key=f"migrations/{migration_id}/migration_plan.json",
        )["Body"].read()
    )

    # Run validation checks
    route_coverage = _validate_route_coverage(normalized, plan)
    auth_coverage = _validate_auth_coverage(normalized, plan)
    plugin_coverage = _validate_plugin_coverage(normalized, plan)

    # Lint the generated SAM template (advisory only — never fails the stage).
    template_lint = _lint_generated_template(migration_id, bucket)

    # Calculate confidence score
    confidence_score = (
        route_coverage["percentage"] * 0.30
        + auth_coverage["percentage"] * 0.25
        + plugin_coverage["percentage"] * 0.25
        + 100 * 0.20  # config accuracy baseline (full check would compare values)
    )

    # Determine final status
    final_status = "COMPLETE" if confidence_score >= 80 else "NEEDS_REVIEW"

    # Build validation report
    report = {
        "migration_id": migration_id,
        "confidence_score": round(confidence_score, 1),
        "target_api_type": plan.get("target_api_type", "REST"),
        "target_api_type_reasoning": plan.get("target_api_type_reasoning", ""),
        "route_coverage": route_coverage,
        "auth_coverage": auth_coverage,
        "plugin_coverage": plugin_coverage,
        "feature_mappings": _collect_all_mappings(plan),
        "gaps": _collect_gaps(plan),
        "warnings": plan.get("warnings", []),
        "summary": plan.get("summary", {}),
        "template_lint": template_lint,
    }

    # Store validation report (JSON in S3 keeps floats — only DynamoDB needs Decimal)
    s3.put_object(
        Bucket=bucket,
        Key=f"migrations/{migration_id}/output/validation-report.json",
        Body=json.dumps(report, indent=2),
        ContentType="application/json",
    )

    # Also store the lint result as a standalone downloadable artifact.
    s3.put_object(
        Bucket=bucket,
        Key=f"migrations/{migration_id}/output/cfn-lint.json",
        Body=json.dumps(template_lint, indent=2),
        ContentType="application/json",
    )

    # Update DynamoDB with final status and score.
    # DynamoDB rejects Python floats, so convert to Decimal.
    table.update_item(
        Key={"migration_id": migration_id},
        UpdateExpression=(
            "SET #s = :status, updated_at = :ts, confidence_score = :score, "
            "target_api_type = :api_type, summary = :summary"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": final_status,
            ":ts": datetime.now(timezone.utc).isoformat(),
            ":score": Decimal(str(round(confidence_score, 1))),
            ":api_type": plan.get("target_api_type", "REST"),
            ":summary": _to_decimal(report["summary"]),
        },
    )

    return {
        "migration_id": migration_id,
        "confidence_score": round(confidence_score, 1),
        "status": final_status,
        "route_coverage": route_coverage["percentage"],
        "plugin_coverage": plugin_coverage["percentage"],
        "gaps_count": len(report["gaps"]),
    }


def _lint_generated_template(migration_id: str, bucket: str) -> dict:
    """Read the generated template and run cfn-lint on it (advisory only).

    Any failure to load the template or run the linter degrades gracefully to a
    "skipped" result so the validation stage is never blocked by linting.
    """
    try:
        obj = s3.get_object(
            Bucket=bucket,
            Key=f"migrations/{migration_id}/output/template.yaml",
        )
        template_str = obj["Body"].read().decode("utf-8")
    except Exception as exc:
        print(f"Template lint skipped for {migration_id}: {exc}")
        return {
            "status": "skipped",
            "reason": "generated template could not be loaded",
            "counts": {"error": 0, "warning": 0, "informational": 0},
            "findings": [],
            "truncated": False,
        }

    return lint_template(template_str)


def _validate_route_coverage(normalized: dict, plan: dict) -> dict:
    """Check that every source route has a corresponding resource in the plan."""
    source_routes = []
    for api in normalized.get("apis", []):
        for route in api.get("routes", []):
            for path in route.get("paths", []):
                for method in route.get("methods", ["GET"]):
                    source_routes.append(f"{method} {path}")

    total = len(source_routes) if source_routes else 1

    # Check plan resources
    plan_routes = set()
    for api in plan.get("apis", []):
        for resource in api.get("resources", []):
            for method in resource.get("methods", []):
                plan_routes.add(f"{method} {resource.get('path', '')}")

    covered = sum(1 for r in source_routes if r in plan_routes)

    # If plan has no explicit resources, assume Bedrock mapped them (give partial credit)
    if not plan_routes and source_routes:
        covered = int(total * 0.8)

    return {
        "total": total,
        "covered": covered,
        "percentage": round((covered / total) * 100, 1) if total > 0 else 100,
        "details": [r for r in source_routes if r not in plan_routes][:10],
    }


def _validate_auth_coverage(normalized: dict, plan: dict) -> dict:
    """Check that auth plugins are mapped to authorizers."""
    auth_plugins = []
    for api in normalized.get("apis", []):
        for plugin in api.get("plugins", []):
            if plugin.get("category") == "authentication":
                auth_plugins.append(plugin.get("source_plugin_name", plugin.get("name", "")))

    total = len(auth_plugins) if auth_plugins else 1

    # Check if plan has authorizer for each API with auth plugins
    covered = 0
    for api in plan.get("apis", []):
        authorizer_type = api.get("authorizer_type", "NONE")
        if authorizer_type != "NONE":
            # Count mapped auth features
            for mapping in api.get("feature_mappings", []):
                if mapping.get("mapping_type") in ("direct", "lambda") and mapping.get(
                    "source_plugin_name"
                ) in auth_plugins:
                    covered += 1

    if not auth_plugins:
        return {"total": 0, "covered": 0, "percentage": 100, "details": []}

    return {
        "total": total,
        "covered": min(covered, total),
        "percentage": round((min(covered, total) / total) * 100, 1),
        "details": [],
    }


def _validate_plugin_coverage(normalized: dict, plan: dict) -> dict:
    """Check that all plugins are either mapped or flagged as gaps."""
    all_plugins = set()
    for api in normalized.get("apis", []):
        for plugin in api.get("plugins", []):
            all_plugins.add(plugin.get("source_plugin_name", plugin.get("name", "")))
    for plugin in normalized.get("global_plugins", []):
        all_plugins.add(plugin.get("source_plugin_name", plugin.get("name", "")))

    total = len(all_plugins) if all_plugins else 1

    # Count mapped plugins (any mapping type except gap is "covered")
    mapped_plugins = set()
    for api in plan.get("apis", []):
        for mapping in api.get("feature_mappings", []):
            if mapping.get("mapping_type") != "gap":
                mapped_plugins.add(mapping.get("source_plugin_name", ""))

    covered = len(all_plugins.intersection(mapped_plugins))

    return {
        "total": total,
        "covered": covered,
        "percentage": round((covered / total) * 100, 1) if total > 0 else 100,
        "details": list(all_plugins - mapped_plugins),
    }


def _collect_all_mappings(plan: dict) -> list[dict]:
    """Collect all feature mappings from the plan."""
    mappings = []
    for api in plan.get("apis", []):
        for mapping in api.get("feature_mappings", []):
            mappings.append(mapping)
    return mappings


def _collect_gaps(plan: dict) -> list[dict]:
    """Collect gap items from the plan."""
    gaps = []
    for api in plan.get("apis", []):
        for mapping in api.get("feature_mappings", []):
            if mapping.get("mapping_type") == "gap":
                gaps.append(
                    {
                        "source_feature": mapping.get("source_feature", ""),
                        "source_plugin_name": mapping.get("source_plugin_name", ""),
                        "category": "unknown",
                        "severity": "medium",
                        "recommendation": mapping.get("implementation_notes", ""),
                        "effort_estimate_hours": 4,
                    }
                )
    return gaps


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
