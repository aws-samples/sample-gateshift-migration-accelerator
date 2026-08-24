"""Shared pytest fixtures for GateShift backend tests."""

import sys
from pathlib import Path

import pytest

# Add src/ to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def basic_kong_yaml():
    """Minimal Kong config with one service and one route."""
    return """
_format_version: "3.0"
services:
  - name: hello-service
    url: http://httpbin.org:80
    routes:
      - name: hello-route
        paths:
          - /hello
        methods:
          - GET
"""


@pytest.fixture
def medium_kong_yaml():
    """Kong config with multiple services, plugins, and consumers."""
    return """
_format_version: "3.0"
services:
  - name: payment-service
    url: http://payment-backend:8080
    routes:
      - name: payments-route
        paths:
          - /api/v1/payments
        methods:
          - POST
          - GET
      - name: payment-detail-route
        paths:
          - /api/v1/payments/{id}
        methods:
          - GET
          - PUT
          - DELETE
    plugins:
      - name: key-auth
        config:
          key_names:
            - apikey
            - x-api-key
      - name: rate-limiting
        config:
          minute: 100
          policy: local
      - name: cors
        config:
          origins:
            - "https://app.example.com"
          methods:
            - GET
            - POST
          headers:
            - Authorization
            - Content-Type
          max_age: 3600

  - name: user-service
    url: http://user-backend:8080
    routes:
      - name: users-route
        paths:
          - /api/v1/users
        methods:
          - GET
          - POST
    plugins:
      - name: jwt
        config:
          claims_to_verify:
            - exp
      - name: request-validator
        config:
          body_schema: '{"type": "object"}'

consumers:
  - username: mobile-app
    keyauth_credentials:
      - key: mobile-app-key-001
  - username: web-frontend
    keyauth_credentials:
      - key: web-frontend-key-001
"""


@pytest.fixture
def complex_kong_yaml():
    """Kong config with upstreams, global plugins, ACLs, and multiple credential types."""
    return """
_format_version: "3.0"
services:
  - name: analytics-service
    host: analytics-upstream
    port: 8080
    protocol: http
    routes:
      - name: analytics-query
        paths:
          - /api/v1/analytics
        methods:
          - POST
      - name: analytics-dashboard
        paths:
          - /api/v1/dashboards
        methods:
          - GET
        hosts:
          - analytics.example.com
        strip_path: false
        preserve_host: true
    plugins:
      - name: oauth2
        config:
          scopes:
            - analytics:read
            - analytics:write
          mandatory_scope: true
      - name: ip-restriction
        config:
          allow:
            - 10.0.0.0/8
          deny:
            - 0.0.0.0/0
      - name: proxy-cache
        config:
          cache_ttl: 300
          content_type:
            - application/json
      - name: bot-detection
        config:
          allow:
            - googlebot

upstreams:
  - name: analytics-upstream
    algorithm: round-robin
    targets:
      - target: analytics-1.internal:8080
        weight: 100
      - target: analytics-2.internal:8080
        weight: 50
    healthchecks:
      active:
        http_path: /health
        healthy:
          interval: 5

consumers:
  - username: internal-service
    keyauth_credentials:
      - key: internal-key
    acls:
      - group: analytics-readers
      - group: analytics-writers
  - username: partner
    custom_id: partner-001
    basicauth_credentials:
      - username: partner
        password: secret

plugins:
  - name: correlation-id
    config:
      header_name: X-Correlation-ID
      generator: uuid
  - name: file-log
    config:
      path: /var/log/kong/access.log
"""


@pytest.fixture
def sample_migration_plan():
    """A sample migration plan as would be produced by the analyzer."""
    return {
        "target_api_type": "REST",
        "target_api_type_reasoning": "REST API needed for usage plans and request validation.",
        "apis": [
            {
                "name": "payment-service",
                "authorizer_type": "API_KEY",
                "resources": [
                    {"path": "/api/v1/payments", "methods": ["GET", "POST"]},
                    {"path": "/api/v1/payments/{id}", "methods": ["GET", "PUT", "DELETE"]},
                ],
                "feature_mappings": [
                    {
                        "source_feature": "Authentication",
                        "source_plugin_name": "key-auth",
                        "aws_equivalent": "API Gateway API Keys + Usage Plans",
                        "mapping_type": "direct",
                        "implementation_notes": "API Keys for metering.",
                    },
                    {
                        "source_feature": "Rate Limiting",
                        "source_plugin_name": "rate-limiting",
                        "aws_equivalent": "Usage Plan Throttling",
                        "mapping_type": "direct",
                        "implementation_notes": "100 req/min → 1.67 req/s rate.",
                    },
                    {
                        "source_feature": "CORS",
                        "source_plugin_name": "cors",
                        "aws_equivalent": "API Gateway CORS Configuration",
                        "mapping_type": "direct",
                        "implementation_notes": "Native CORS.",
                    },
                ],
            },
            {
                "name": "user-service",
                "authorizer_type": "LAMBDA",
                "resources": [
                    {"path": "/api/v1/users", "methods": ["GET", "POST"]},
                ],
                "feature_mappings": [
                    {
                        "source_feature": "Authentication",
                        "source_plugin_name": "jwt",
                        "aws_equivalent": "Lambda Authorizer (TOKEN type)",
                        "mapping_type": "lambda",
                        "implementation_notes": "Validate JWT in Lambda.",
                    },
                    {
                        "source_feature": "Validation",
                        "source_plugin_name": "request-validator",
                        "aws_equivalent": "API Gateway Request Validators",
                        "mapping_type": "direct",
                        "implementation_notes": "JSON Schema validation.",
                    },
                ],
            },
        ],
        "summary": {
            "direct_count": 4,
            "lambda_count": 1,
            "alternative_count": 0,
            "gap_count": 0,
            "estimated_effort_hours": 8,
        },
        "warnings": [
            "Kong rate-limiting uses 'local' policy (per-node). API Gateway throttling is global."
        ],
    }


@pytest.fixture
def sample_migration_plan_with_gaps():
    """Migration plan with gap features."""
    return {
        "target_api_type": "REST",
        "target_api_type_reasoning": "REST API needed.",
        "apis": [
            {
                "name": "my-service",
                "authorizer_type": "NONE",
                "resources": [],
                "feature_mappings": [
                    {
                        "source_feature": "CORS",
                        "source_plugin_name": "cors",
                        "aws_equivalent": "API Gateway CORS",
                        "mapping_type": "direct",
                        "implementation_notes": "Native support.",
                    },
                    {
                        "source_feature": "Custom Logic",
                        "source_plugin_name": "custom-lua-plugin",
                        "aws_equivalent": "—",
                        "mapping_type": "gap",
                        "implementation_notes": "Rewrite in Lambda.",
                    },
                    {
                        "source_feature": "Rate Limiting",
                        "source_plugin_name": "rate-limiting",
                        "aws_equivalent": "Usage Plan",
                        "mapping_type": "direct",
                        "implementation_notes": "Map to usage plan.",
                    },
                ],
            }
        ],
        "summary": {
            "direct_count": 2,
            "lambda_count": 0,
            "alternative_count": 0,
            "gap_count": 1,
            "estimated_effort_hours": 6,
        },
        "warnings": ["Custom Lua plugin has no AWS equivalent."],
    }
