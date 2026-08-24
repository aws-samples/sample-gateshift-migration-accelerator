"""Kong declarative YAML parser for GateShift."""

from __future__ import annotations

import yaml

from .models import (
    NormalizedAPI,
    NormalizedBackend,
    NormalizedConfig,
    NormalizedConsumer,
    NormalizedPlugin,
    NormalizedRoute,
    PluginCategory,
)

PLUGIN_CATEGORY_MAP: dict[str, PluginCategory] = {
    # Authentication
    "key-auth": PluginCategory.AUTHENTICATION,
    "jwt": PluginCategory.AUTHENTICATION,
    "oauth2": PluginCategory.AUTHENTICATION,
    "basic-auth": PluginCategory.AUTHENTICATION,
    "hmac-auth": PluginCategory.AUTHENTICATION,
    "ldap-auth": PluginCategory.AUTHENTICATION,
    "mtls-auth": PluginCategory.AUTHENTICATION,
    "acl": PluginCategory.AUTHENTICATION,
    "session": PluginCategory.AUTHENTICATION,
    # Rate Limiting
    "rate-limiting": PluginCategory.RATE_LIMITING,
    "response-ratelimiting": PluginCategory.RATE_LIMITING,
    "request-size-limiting": PluginCategory.RATE_LIMITING,
    # Transformation
    "request-transformer": PluginCategory.TRANSFORMATION,
    "request-transformer-advanced": PluginCategory.TRANSFORMATION,
    "response-transformer": PluginCategory.TRANSFORMATION,
    "response-transformer-advanced": PluginCategory.TRANSFORMATION,
    "correlation-id": PluginCategory.TRANSFORMATION,
    "grpc-gateway": PluginCategory.TRANSFORMATION,
    "grpc-web": PluginCategory.TRANSFORMATION,
    # Security
    "ip-restriction": PluginCategory.SECURITY,
    "bot-detection": PluginCategory.SECURITY,
    # CORS
    "cors": PluginCategory.CORS,
    # Logging
    "file-log": PluginCategory.LOGGING,
    "http-log": PluginCategory.LOGGING,
    "tcp-log": PluginCategory.LOGGING,
    "udp-log": PluginCategory.LOGGING,
    "syslog": PluginCategory.LOGGING,
    "datadog": PluginCategory.LOGGING,
    "prometheus": PluginCategory.LOGGING,
    "opentelemetry": PluginCategory.LOGGING,
    "zipkin": PluginCategory.LOGGING,
    # Caching
    "proxy-cache": PluginCategory.CACHING,
    "proxy-cache-advanced": PluginCategory.CACHING,
    # Validation
    "request-validator": PluginCategory.VALIDATION,
}


class KongParser:
    """Parse Kong declarative YAML into normalized IR."""

    def parse(self, raw_yaml: str) -> NormalizedConfig:
        """Parse raw Kong declarative YAML string into NormalizedConfig."""
        config = yaml.safe_load(raw_yaml)

        if not config or not isinstance(config, dict):
            raise ValueError("Invalid Kong configuration: empty or not a mapping")

        format_version = config.get("_format_version", "")

        services = config.get("services", [])
        consumers = config.get("consumers", [])
        upstreams = config.get("upstreams", [])
        global_plugins = config.get("plugins", [])

        normalized_apis = self._parse_services(services, upstreams)
        normalized_consumers = self._parse_consumers(consumers)
        normalized_global_plugins = self._parse_plugins(global_plugins, scope="global")

        return NormalizedConfig(
            source_platform="kong",
            source_version=str(format_version),
            apis=normalized_apis,
            consumers=normalized_consumers,
            global_plugins=normalized_global_plugins,
        )

    def _parse_services(
        self, services: list[dict], upstreams: list[dict]
    ) -> list[NormalizedAPI]:
        """Convert Kong services into normalized APIs."""
        apis = []

        for service in services:
            name = service.get("name", "unnamed-service")
            backend = self._resolve_backend(service, upstreams)
            routes = self._parse_routes(service.get("routes", []))
            plugins = self._parse_plugins(service.get("plugins", []), scope="service")

            apis.append(
                NormalizedAPI(
                    name=name,
                    backend=backend,
                    routes=routes,
                    plugins=plugins,
                )
            )

        return apis

    def _resolve_backend(
        self, service: dict, upstreams: list[dict]
    ) -> NormalizedBackend:
        """Resolve service backend URL, including upstream targets."""
        url = service.get("url", "")

        if not url:
            protocol = service.get("protocol", "http")
            host = service.get("host", "localhost")
            port = service.get("port", 80)
            path = service.get("path", "")
            url = f"{protocol}://{host}:{port}{path}"

        # Check if host matches an upstream name
        host = service.get("host", "")
        targets: list[dict] = []
        health_checks = None

        for upstream in upstreams:
            if upstream.get("name") == host:
                targets = [
                    {"target": t.get("target", ""), "weight": t.get("weight", 100)}
                    for t in upstream.get("targets", [])
                ]
                health_checks = upstream.get("healthchecks")
                break

        return NormalizedBackend(
            url=url,
            protocol=service.get("protocol", "http"),
            connect_timeout=service.get("connect_timeout", 60000),
            read_timeout=service.get("read_timeout", 60000),
            write_timeout=service.get("write_timeout", 60000),
            retries=service.get("retries", 5),
            targets=targets,
            health_checks=health_checks,
        )

    def _parse_routes(self, routes: list[dict]) -> list[NormalizedRoute]:
        """Convert Kong routes into normalized routes."""
        normalized = []

        for route in routes:
            normalized.append(
                NormalizedRoute(
                    name=route.get("name", ""),
                    paths=route.get("paths", []),
                    methods=route.get("methods", ["GET"]),
                    hosts=route.get("hosts", []),
                    strip_path=route.get("strip_path", True),
                    preserve_host=route.get("preserve_host", False),
                    protocols=route.get("protocols", ["http", "https"]),
                )
            )

        return normalized

    def _parse_plugins(
        self, plugins: list[dict], scope: str
    ) -> list[NormalizedPlugin]:
        """Convert Kong plugins into normalized plugins."""
        normalized = []

        for plugin in plugins:
            plugin_name = plugin.get("name", "unknown")
            category = PLUGIN_CATEGORY_MAP.get(plugin_name, PluginCategory.OTHER)

            normalized.append(
                NormalizedPlugin(
                    name=plugin_name,
                    category=category,
                    scope=scope,
                    config=plugin.get("config", {}),
                    source_plugin_name=plugin_name,
                )
            )

        return normalized

    def _parse_consumers(self, consumers: list[dict]) -> list[NormalizedConsumer]:
        """Convert Kong consumers into normalized consumers."""
        normalized = []

        for consumer in consumers:
            credentials = []

            # Collect all credential types
            for cred_type in ["keyauth_credentials", "jwt_secrets", "basicauth_credentials"]:
                for cred in consumer.get(cred_type, []):
                    credentials.append({"type": cred_type, **cred})

            groups = []
            for acl in consumer.get("acls", []):
                group = acl.get("group", "")
                if group:
                    groups.append(group)

            normalized.append(
                NormalizedConsumer(
                    username=consumer.get("username", ""),
                    custom_id=consumer.get("custom_id"),
                    credentials=credentials,
                    groups=groups,
                )
            )

        return normalized
