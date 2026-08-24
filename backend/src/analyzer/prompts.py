"""Bedrock prompt templates for GateShift analysis."""

from __future__ import annotations

ANALYSIS_SYSTEM_PROMPT = """You are an AWS Solutions Architect specializing in API Gateway migrations.
You analyze 3rd-party API gateway configurations and produce migration plans to Amazon API Gateway.

You are precise, practical, and focus on deployable outcomes. When mapping features:
- Prefer native API Gateway features over Lambda when possible
- Flag behavioral differences (e.g., per-node vs global rate limiting)
- Recommend REST API when usage plans, caching, WAF, or request validation are needed
- Recommend HTTP API when lower cost/latency is priority and features are simple
"""


def build_analysis_prompt(normalized_config: dict, deterministic_mappings: list[dict]) -> str:
    """Build the analysis prompt for Bedrock."""
    import json

    return f"""Analyze this normalized API gateway configuration and produce a complete migration plan.

## Pre-computed Mappings (verified correct)
The following plugin mappings have already been determined:
{json.dumps(deterministic_mappings, indent=2)}

## Source Configuration (Normalized)
{json.dumps(normalized_config, indent=2)}

## Your Task
1. Review the pre-computed mappings and confirm or adjust them based on the specific config values.
2. For any plugins NOT in the pre-computed list, determine the AWS equivalent.
3. Decide whether the target should be REST API or HTTP API based on the feature requirements.
4. Identify any interactions between plugins that affect the migration approach.
5. Estimate effort in hours for the overall migration.

Use the create_migration_plan tool to output your structured analysis."""


MIGRATION_PLAN_TOOL = {
    "toolSpec": {
        "name": "create_migration_plan",
        "description": "Output a structured migration plan for converting the source API gateway config to Amazon API Gateway",
        "inputSchema": {
            "json": {
                "type": "object",
                "required": ["target_api_type", "target_api_type_reasoning", "apis", "summary", "warnings"],
                "properties": {
                    "target_api_type": {
                        "type": "string",
                        "enum": ["REST", "HTTP"],
                        "description": "Recommended API Gateway type",
                    },
                    "target_api_type_reasoning": {
                        "type": "string",
                        "description": "Explanation for why this API type was chosen",
                    },
                    "apis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "resources", "feature_mappings"],
                            "properties": {
                                "name": {"type": "string"},
                                "resources": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "path": {"type": "string"},
                                            "methods": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                            "integration_type": {"type": "string"},
                                            "backend_url": {"type": "string"},
                                        },
                                    },
                                },
                                "authorizer_type": {
                                    "type": "string",
                                    "enum": ["NONE", "API_KEY", "LAMBDA", "COGNITO", "IAM"],
                                },
                                "feature_mappings": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": [
                                            "source_feature",
                                            "source_plugin_name",
                                            "aws_equivalent",
                                            "mapping_type",
                                            "implementation_notes",
                                        ],
                                        "properties": {
                                            "source_feature": {"type": "string"},
                                            "source_plugin_name": {"type": "string"},
                                            "aws_equivalent": {"type": "string"},
                                            "mapping_type": {
                                                "type": "string",
                                                "enum": ["direct", "lambda", "alternative", "gap"],
                                            },
                                            "implementation_notes": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "summary": {
                        "type": "object",
                        "required": ["direct_count", "lambda_count", "alternative_count", "gap_count", "estimated_effort_hours"],
                        "properties": {
                            "direct_count": {"type": "integer"},
                            "lambda_count": {"type": "integer"},
                            "alternative_count": {"type": "integer"},
                            "gap_count": {"type": "integer"},
                            "estimated_effort_hours": {"type": "number"},
                        },
                    },
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Important migration warnings or behavioral differences",
                    },
                },
            }
        },
    }
}
