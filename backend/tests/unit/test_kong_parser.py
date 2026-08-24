"""Unit tests for the Kong declarative YAML parser."""

import pytest

from parser.kong_parser import KongParser, PLUGIN_CATEGORY_MAP
from parser.models import (
    NormalizedConfig,
    NormalizedAPI,
    NormalizedRoute,
    NormalizedPlugin,
    NormalizedConsumer,
    NormalizedBackend,
    PluginCategory,
)


class TestKongParserBasic:
    """Tests for basic parsing functionality."""

    def setup_method(self):
        self.parser = KongParser()

    def test_parse_returns_normalized_config(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert isinstance(result, NormalizedConfig)

    def test_parse_sets_source_platform_to_kong(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert result.source_platform == "kong"

    def test_parse_captures_format_version(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert result.source_version == "3.0"

    def test_parse_single_service(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert len(result.apis) == 1
        assert result.apis[0].name == "hello-service"

    def test_parse_single_route(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        api = result.apis[0]
        assert len(api.routes) == 1
        route = api.routes[0]
        assert route.name == "hello-route"
        assert route.paths == ["/hello"]
        assert route.methods == ["GET"]

    def test_parse_backend_url(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        backend = result.apis[0].backend
        assert backend.url == "http://httpbin.org:80"

    def test_parse_no_plugins(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert result.apis[0].plugins == []

    def test_parse_no_consumers(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert result.consumers == []

    def test_parse_no_global_plugins(self, basic_kong_yaml):
        result = self.parser.parse(basic_kong_yaml)
        assert result.global_plugins == []


class TestKongParserInvalidInput:
    """Tests for invalid/edge-case inputs."""

    def setup_method(self):
        self.parser = KongParser()

    def test_parse_empty_string_raises_error(self):
        with pytest.raises(ValueError, match="Invalid Kong configuration"):
            self.parser.parse("")

    def test_parse_non_mapping_raises_error(self):
        with pytest.raises(ValueError, match="Invalid Kong configuration"):
            self.parser.parse("- item1\n- item2")

    def test_parse_null_yaml_raises_error(self):
        with pytest.raises(ValueError, match="Invalid Kong configuration"):
            self.parser.parse("null")

    def test_parse_invalid_yaml_raises_error(self):
        with pytest.raises(Exception):
            self.parser.parse("{{invalid: yaml: content")

    def test_parse_empty_services_list(self):
        result = self.parser.parse("_format_version: '3.0'\nservices: []")
        assert result.apis == []

    def test_parse_missing_services_key(self):
        result = self.parser.parse("_format_version: '3.0'\nsome_key: value")
        assert result.apis == []


class TestKongParserMultipleServices:
    """Tests for configs with multiple services and plugins."""

    def setup_method(self):
        self.parser = KongParser()

    def test_parse_two_services(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        assert len(result.apis) == 2

    def test_parse_service_names(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        names = [api.name for api in result.apis]
        assert "payment-service" in names
        assert "user-service" in names

    def test_parse_multiple_routes_per_service(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        assert len(payment_api.routes) == 2

    def test_parse_route_methods(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        payments_route = next(r for r in payment_api.routes if r.name == "payments-route")
        assert set(payments_route.methods) == {"POST", "GET"}

    def test_parse_plugins_on_service(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        assert len(payment_api.plugins) == 3

    def test_parse_plugin_names(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        plugin_names = [p.name for p in payment_api.plugins]
        assert "key-auth" in plugin_names
        assert "rate-limiting" in plugin_names
        assert "cors" in plugin_names

    def test_parse_plugin_categories(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        categories = {p.name: p.category for p in payment_api.plugins}
        assert categories["key-auth"] == PluginCategory.AUTHENTICATION
        assert categories["rate-limiting"] == PluginCategory.RATE_LIMITING
        assert categories["cors"] == PluginCategory.CORS

    def test_parse_plugin_config(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        rate_plugin = next(p for p in payment_api.plugins if p.name == "rate-limiting")
        assert rate_plugin.config["minute"] == 100
        assert rate_plugin.config["policy"] == "local"

    def test_parse_plugin_scope_is_service(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        payment_api = next(a for a in result.apis if a.name == "payment-service")
        for plugin in payment_api.plugins:
            assert plugin.scope == "service"

    def test_parse_consumers(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        assert len(result.consumers) == 2

    def test_parse_consumer_credentials(self, medium_kong_yaml):
        result = self.parser.parse(medium_kong_yaml)
        mobile_consumer = next(c for c in result.consumers if c.username == "mobile-app")
        assert len(mobile_consumer.credentials) == 1
        assert mobile_consumer.credentials[0]["key"] == "mobile-app-key-001"
        assert mobile_consumer.credentials[0]["type"] == "keyauth_credentials"


class TestKongParserComplex:
    """Tests for complex configs with upstreams, global plugins, and ACLs."""

    def setup_method(self):
        self.parser = KongParser()

    def test_parse_upstream_targets(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        assert len(api.backend.targets) == 2
        assert api.backend.targets[0]["target"] == "analytics-1.internal:8080"
        assert api.backend.targets[0]["weight"] == 100
        assert api.backend.targets[1]["target"] == "analytics-2.internal:8080"
        assert api.backend.targets[1]["weight"] == 50

    def test_parse_upstream_health_checks(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        assert api.backend.health_checks is not None
        assert "active" in api.backend.health_checks

    def test_parse_backend_url_from_host_port(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        assert api.backend.url == "http://analytics-upstream:8080"

    def test_parse_global_plugins(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        assert len(result.global_plugins) == 2
        plugin_names = [p.name for p in result.global_plugins]
        assert "correlation-id" in plugin_names
        assert "file-log" in plugin_names

    def test_parse_global_plugins_have_global_scope(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        for plugin in result.global_plugins:
            assert plugin.scope == "global"

    def test_parse_consumer_acl_groups(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        internal = next(c for c in result.consumers if c.username == "internal-service")
        assert "analytics-readers" in internal.groups
        assert "analytics-writers" in internal.groups

    def test_parse_consumer_custom_id(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        partner = next(c for c in result.consumers if c.username == "partner")
        assert partner.custom_id == "partner-001"

    def test_parse_consumer_basic_auth_credentials(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        partner = next(c for c in result.consumers if c.username == "partner")
        basic_creds = [c for c in partner.credentials if c["type"] == "basicauth_credentials"]
        assert len(basic_creds) == 1
        assert basic_creds[0]["username"] == "partner"

    def test_parse_route_hosts(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        dashboard_route = next(r for r in api.routes if r.name == "analytics-dashboard")
        assert "analytics.example.com" in dashboard_route.hosts

    def test_parse_route_strip_path_false(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        dashboard_route = next(r for r in api.routes if r.name == "analytics-dashboard")
        assert dashboard_route.strip_path is False

    def test_parse_route_preserve_host_true(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        dashboard_route = next(r for r in api.routes if r.name == "analytics-dashboard")
        assert dashboard_route.preserve_host is True

    def test_parse_service_level_plugin_config(self, complex_kong_yaml):
        result = self.parser.parse(complex_kong_yaml)
        api = result.apis[0]
        ip_plugin = next(p for p in api.plugins if p.name == "ip-restriction")
        assert ip_plugin.config["allow"] == ["10.0.0.0/8"]
        assert ip_plugin.config["deny"] == ["0.0.0.0/0"]


class TestPluginCategoryMap:
    """Tests for the plugin category mapping dictionary."""

    def test_all_auth_plugins_categorized(self):
        auth_plugins = ["key-auth", "jwt", "oauth2", "basic-auth", "hmac-auth", "ldap-auth", "mtls-auth", "acl"]
        for plugin in auth_plugins:
            assert PLUGIN_CATEGORY_MAP[plugin] == PluginCategory.AUTHENTICATION

    def test_all_rate_limiting_plugins_categorized(self):
        rl_plugins = ["rate-limiting", "response-ratelimiting", "request-size-limiting"]
        for plugin in rl_plugins:
            assert PLUGIN_CATEGORY_MAP[plugin] == PluginCategory.RATE_LIMITING

    def test_all_logging_plugins_categorized(self):
        log_plugins = ["file-log", "http-log", "tcp-log", "udp-log", "syslog", "datadog", "prometheus"]
        for plugin in log_plugins:
            assert PLUGIN_CATEGORY_MAP[plugin] == PluginCategory.LOGGING

    def test_unknown_plugin_returns_other(self):
        parser = KongParser()
        result = parser.parse("""
_format_version: "3.0"
services:
  - name: test
    url: http://backend:80
    plugins:
      - name: my-custom-plugin
        config: {}
""")
        plugin = result.apis[0].plugins[0]
        assert plugin.category == PluginCategory.OTHER

    def test_cors_plugin_categorized(self):
        assert PLUGIN_CATEGORY_MAP["cors"] == PluginCategory.CORS

    def test_security_plugins_categorized(self):
        assert PLUGIN_CATEGORY_MAP["ip-restriction"] == PluginCategory.SECURITY
        assert PLUGIN_CATEGORY_MAP["bot-detection"] == PluginCategory.SECURITY
