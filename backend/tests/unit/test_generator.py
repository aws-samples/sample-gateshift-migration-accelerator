"""Unit tests for the SAM template generator."""

import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock boto3 before importing handler
sys.modules["boto3"] = MagicMock()

from generator.handler import (
    _generate_sam_template,
    _build_auth_config,
    _has_rate_limiting,
    _generate_authorizer_code,
    _generate_report_markdown,
    _sanitize_logical_id,
    _extract_rate_config,
)


class TestSanitizeLogicalId:
    """Tests for CloudFormation logical ID sanitization."""

    def test_simple_name(self):
        assert _sanitize_logical_id("payment") == "Payment"

    def test_hyphenated_name(self):
        assert _sanitize_logical_id("payment-service") == "PaymentService"

    def test_underscored_name(self):
        assert _sanitize_logical_id("user_api") == "UserApi"

    def test_dotted_name(self):
        assert _sanitize_logical_id("api.v1.users") == "ApiV1Users"

    def test_name_with_numbers(self):
        assert _sanitize_logical_id("service-v2") == "ServiceV2"

    def test_already_camel_case(self):
        assert _sanitize_logical_id("MyService") == "Myservice"

    def test_empty_string(self):
        assert _sanitize_logical_id("") == ""


class TestGenerateSamTemplate:
    """Tests for SAM template generation."""

    def test_template_has_required_top_level_keys(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert "AWSTemplateFormatVersion" in template
        assert "Transform" in template
        assert "Resources" in template
        assert "Outputs" in template

    def test_template_format_version(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_transform(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert template["Transform"] == "AWS::Serverless-2016-10-31"

    def test_rest_api_creates_serverless_api(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        resources = template["Resources"]
        # payment-service → PaymentServiceApi
        assert "PaymentServiceApi" in resources
        assert resources["PaymentServiceApi"]["Type"] == "AWS::Serverless::Api"

    def test_http_api_creates_serverless_http_api(self):
        plan = {
            "target_api_type": "HTTP",
            "apis": [{"name": "my-service", "authorizer_type": "NONE", "feature_mappings": []}],
            "summary": {},
            "warnings": [],
        }
        template = _generate_sam_template(plan)
        assert "MyServiceHttpApi" in template["Resources"]
        assert template["Resources"]["MyServiceHttpApi"]["Type"] == "AWS::Serverless::HttpApi"

    def test_api_key_auth_config(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        api_props = template["Resources"]["PaymentServiceApi"]["Properties"]
        assert "Auth" in api_props
        assert api_props["Auth"]["ApiKeyRequired"] is True

    def test_lambda_authorizer_creates_function(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert "UserServiceAuthorizerFunction" in template["Resources"]
        func = template["Resources"]["UserServiceAuthorizerFunction"]
        assert func["Type"] == "AWS::Serverless::Function"
        assert func["Properties"]["Runtime"] == "python3.12"

    def test_lambda_auth_config(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        api_props = template["Resources"]["UserServiceApi"]["Properties"]
        assert api_props["Auth"]["DefaultAuthorizer"] == "TokenAuthorizer"

    def test_usage_plan_created_for_rate_limiting(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert "PaymentServiceUsagePlan" in template["Resources"]
        usage_plan = template["Resources"]["PaymentServiceUsagePlan"]
        assert usage_plan["Type"] == "AWS::ApiGateway::UsagePlan"

    def test_no_usage_plan_without_rate_limiting(self):
        plan = {
            "target_api_type": "REST",
            "apis": [{"name": "simple", "authorizer_type": "NONE", "feature_mappings": []}],
            "summary": {},
            "warnings": [],
        }
        template = _generate_sam_template(plan)
        assert "SimpleUsagePlan" not in template["Resources"]

    def test_outputs_contain_endpoint(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert "PaymentServiceEndpoint" in template["Outputs"]
        assert "UserServiceEndpoint" in template["Outputs"]

    def test_cors_globals_present(self, sample_migration_plan):
        template = _generate_sam_template(sample_migration_plan)
        assert "Globals" in template
        cors = template["Globals"]["Api"]["Cors"]
        assert "AllowMethods" in cors
        assert "AllowOrigin" in cors

    def test_empty_plan_produces_valid_template(self):
        plan = {"target_api_type": "REST", "apis": [], "summary": {}, "warnings": []}
        template = _generate_sam_template(plan)
        assert template["Resources"] == {}
        assert template["Outputs"] == {}


class TestBuildAuthConfig:
    """Tests for auth configuration building."""

    def test_none_authorizer_returns_none(self):
        api = {"authorizer_type": "NONE"}
        assert _build_auth_config(api, "Test") is None

    def test_api_key_returns_config(self):
        api = {"authorizer_type": "API_KEY"}
        config = _build_auth_config(api, "Test")
        assert config["ApiKeyRequired"] is True

    def test_lambda_returns_authorizer_config(self):
        api = {"authorizer_type": "LAMBDA"}
        config = _build_auth_config(api, "MyService")
        assert config["DefaultAuthorizer"] == "TokenAuthorizer"
        assert "TokenAuthorizer" in config["Authorizers"]
        fn_arn = config["Authorizers"]["TokenAuthorizer"]["FunctionArn"]
        assert fn_arn == {"Fn::GetAtt": ["MyServiceAuthorizerFunction", "Arn"]}

    def test_cognito_returns_config(self):
        api = {"authorizer_type": "COGNITO"}
        config = _build_auth_config(api, "Test")
        assert config["DefaultAuthorizer"] == "CognitoAuthorizer"

    def test_unknown_authorizer_returns_none(self):
        api = {"authorizer_type": "UNKNOWN_TYPE"}
        assert _build_auth_config(api, "Test") is None


class TestHasRateLimiting:
    """Tests for rate limiting detection."""

    def test_detects_rate_limiting_plugin(self):
        api = {
            "feature_mappings": [
                {"source_plugin_name": "rate-limiting", "mapping_type": "direct"}
            ]
        }
        assert _has_rate_limiting(api) is True

    def test_detects_response_ratelimiting(self):
        api = {
            "feature_mappings": [
                {"source_plugin_name": "response-ratelimiting", "mapping_type": "direct"}
            ]
        }
        assert _has_rate_limiting(api) is True

    def test_no_rate_limiting(self):
        api = {
            "feature_mappings": [
                {"source_plugin_name": "cors", "mapping_type": "direct"}
            ]
        }
        assert _has_rate_limiting(api) is False

    def test_empty_feature_mappings(self):
        api = {"feature_mappings": []}
        assert _has_rate_limiting(api) is False

    def test_missing_feature_mappings_key(self):
        api = {}
        assert _has_rate_limiting(api) is False


class TestGenerateAuthorizerCode:
    """Tests for Lambda authorizer code generation."""

    def test_generates_code_when_lambda_authorizer_needed(self, sample_migration_plan):
        code = _generate_authorizer_code(sample_migration_plan)
        assert code is not None
        assert "def handler(event, context):" in code
        assert "jwt.decode" in code

    def test_no_code_when_no_lambda_authorizer(self):
        plan = {
            "apis": [{"authorizer_type": "API_KEY"}, {"authorizer_type": "NONE"}]
        }
        code = _generate_authorizer_code(plan)
        assert code is None

    def test_generated_code_has_policy_function(self, sample_migration_plan):
        code = _generate_authorizer_code(sample_migration_plan)
        assert "_generate_policy" in code

    def test_generated_code_handles_bearer_prefix(self, sample_migration_plan):
        code = _generate_authorizer_code(sample_migration_plan)
        assert "bearer" in code.lower()

    def test_generated_code_handles_expired_token(self, sample_migration_plan):
        code = _generate_authorizer_code(sample_migration_plan)
        assert "ExpiredSignatureError" in code


class TestGenerateReportMarkdown:
    """Tests for migration report markdown generation."""

    def test_report_contains_title(self, sample_migration_plan):
        report = _generate_report_markdown(sample_migration_plan)
        assert "# GateShift Migration Report" in report

    def test_report_contains_target_api_type(self, sample_migration_plan):
        report = _generate_report_markdown(sample_migration_plan)
        assert "REST API" in report

    def test_report_contains_summary_table(self, sample_migration_plan):
        report = _generate_report_markdown(sample_migration_plan)
        assert "Direct Mappings" in report
        assert "Lambda Required" in report

    def test_report_contains_api_names(self, sample_migration_plan):
        report = _generate_report_markdown(sample_migration_plan)
        assert "payment-service" in report
        assert "user-service" in report

    def test_report_contains_warnings(self, sample_migration_plan):
        report = _generate_report_markdown(sample_migration_plan)
        assert "⚠️" in report
        assert "per-node" in report

    def test_report_contains_next_steps(self, sample_migration_plan):
        report = _generate_report_markdown(sample_migration_plan)
        assert "sam build" in report
        assert "sam deploy" in report

    def test_report_with_no_warnings(self):
        plan = {
            "target_api_type": "HTTP",
            "target_api_type_reasoning": "Simple proxy",
            "apis": [],
            "summary": {"direct_count": 1, "lambda_count": 0, "alternative_count": 0, "gap_count": 0, "estimated_effort_hours": 2},
            "warnings": [],
        }
        report = _generate_report_markdown(plan)
        assert "## Warnings" not in report
