"""Deterministic Kong plugin → AWS service mapping for GateShift."""

from __future__ import annotations

KONG_TO_AWS_MAP: dict[str, dict] = {
    "key-auth": {
        "aws_service": "API Gateway API Keys + Usage Plans",
        "mapping_type": "direct",
        "api_type_required": "REST",
        "implementation_notes": (
            "API Keys in API Gateway are for metering/throttling, not security. "
            "Combine with a Lambda authorizer for authentication."
        ),
    },
    "jwt": {
        "aws_service": "Lambda Authorizer (TOKEN type)",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": (
            "Validate JWT claims in Lambda, return IAM policy. "
            "Enable authorizer caching (TTL 300s) for performance."
        ),
    },
    "oauth2": {
        "aws_service": "Cognito User Pool Authorizer or Lambda Authorizer",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": (
            "If standard OIDC/OAuth2 flows, use Cognito. "
            "Custom grant types or token introspection require Lambda authorizer."
        ),
    },
    "basic-auth": {
        "aws_service": "Lambda Authorizer",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": "No native basic-auth support. Implement validation in Lambda.",
    },
    "hmac-auth": {
        "aws_service": "Lambda Authorizer",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": "Implement HMAC signature verification in Lambda authorizer.",
    },
    "ldap-auth": {
        "aws_service": "Lambda Authorizer (VPC-connected)",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": "Lambda in VPC to reach LDAP server. Consider caching auth results.",
    },
    "mtls-auth": {
        "aws_service": "Mutual TLS on Custom Domain",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "Configure truststore on API Gateway custom domain name.",
    },
    "acl": {
        "aws_service": "Lambda Authorizer (group-based policy)",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": (
            "Lambda checks consumer group membership and returns scoped IAM policy."
        ),
    },
    "rate-limiting": {
        "aws_service": "Usage Plan Throttling",
        "mapping_type": "direct",
        "api_type_required": "REST",
        "implementation_notes": (
            "Map Kong minute/second/hour limits to API Gateway rate + burst. "
            "Note: Kong 'local' policy is per-node; API Gateway throttling is global."
        ),
    },
    "response-ratelimiting": {
        "aws_service": "Usage Plan Throttling",
        "mapping_type": "direct",
        "api_type_required": "REST",
        "implementation_notes": "Map to per-method throttle settings in Usage Plan.",
    },
    "request-size-limiting": {
        "aws_service": "API Gateway built-in payload limit",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "API Gateway has a 10MB payload limit. Additional validation via request validator.",
    },
    "cors": {
        "aws_service": "API Gateway CORS Configuration",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "Native CORS support on both REST and HTTP APIs.",
    },
    "ip-restriction": {
        "aws_service": "Resource Policy or AWS WAF IP Sets",
        "mapping_type": "direct",
        "api_type_required": "REST",
        "implementation_notes": (
            "Simple allow/deny → Resource Policy. "
            "Complex rules or rate-based blocking → AWS WAF."
        ),
    },
    "bot-detection": {
        "aws_service": "AWS WAF Bot Control",
        "mapping_type": "alternative",
        "api_type_required": "REST",
        "implementation_notes": "Use AWS WAF Bot Control managed rule group.",
    },
    "request-transformer": {
        "aws_service": "VTL Mapping Templates or Lambda",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": (
            "Simple header/query param changes → VTL mapping templates. "
            "Complex body transforms → Lambda integration."
        ),
    },
    "response-transformer": {
        "aws_service": "VTL Mapping Templates or Lambda",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": "Same as request-transformer but on response path.",
    },
    "correlation-id": {
        "aws_service": "API Gateway $context.requestId",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "Use $context.requestId or $context.extendedRequestId via mapping template.",
    },
    "proxy-cache": {
        "aws_service": "API Gateway Stage Caching",
        "mapping_type": "direct",
        "api_type_required": "REST",
        "implementation_notes": "Per-stage caching with configurable TTL. REST API only.",
    },
    "request-validator": {
        "aws_service": "API Gateway Request Validators",
        "mapping_type": "direct",
        "api_type_required": "REST",
        "implementation_notes": "Validates body (JSON Schema), query parameters, and headers.",
    },
    "file-log": {
        "aws_service": "CloudWatch Logs (Access Logging)",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "Configure access log format on API Gateway stage.",
    },
    "http-log": {
        "aws_service": "CloudWatch Logs + Kinesis Firehose",
        "mapping_type": "alternative",
        "api_type_required": None,
        "implementation_notes": "Use CloudWatch subscription filter to forward to HTTP endpoint via Firehose.",
    },
    "tcp-log": {
        "aws_service": "CloudWatch Logs + Kinesis Firehose",
        "mapping_type": "alternative",
        "api_type_required": None,
        "implementation_notes": "Forward logs via Firehose to TCP destination.",
    },
    "datadog": {
        "aws_service": "CloudWatch Metrics + Datadog AWS Integration",
        "mapping_type": "alternative",
        "api_type_required": None,
        "implementation_notes": "Use Datadog's AWS integration to pull CloudWatch metrics.",
    },
    "prometheus": {
        "aws_service": "Amazon Managed Prometheus + CloudWatch",
        "mapping_type": "alternative",
        "api_type_required": None,
        "implementation_notes": "Export CloudWatch metrics to AMP or use custom metrics from Lambda.",
    },
    "opentelemetry": {
        "aws_service": "AWS X-Ray + CloudWatch",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "Enable X-Ray tracing on API Gateway stage.",
    },
    "zipkin": {
        "aws_service": "AWS X-Ray",
        "mapping_type": "direct",
        "api_type_required": None,
        "implementation_notes": "X-Ray provides distributed tracing similar to Zipkin.",
    },
    "session": {
        "aws_service": "Lambda + DynamoDB",
        "mapping_type": "lambda",
        "api_type_required": None,
        "implementation_notes": "No native session support. Implement cookie-based sessions in Lambda with DynamoDB backend.",
    },
}


def get_mapping(plugin_name: str) -> dict | None:
    """Get the AWS mapping for a Kong plugin, or None if unknown."""
    return KONG_TO_AWS_MAP.get(plugin_name)


def get_all_mappable_plugins() -> list[str]:
    """Return list of all Kong plugins we have mappings for."""
    return list(KONG_TO_AWS_MAP.keys())
