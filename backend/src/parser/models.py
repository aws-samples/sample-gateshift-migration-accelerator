"""Normalized Intermediate Representation (IR) models for GateShift."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PluginCategory(str, Enum):
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    TRANSFORMATION = "transformation"
    SECURITY = "security"
    LOGGING = "logging"
    CACHING = "caching"
    VALIDATION = "validation"
    CORS = "cors"
    OTHER = "other"


class MappingType(str, Enum):
    DIRECT = "direct"
    LAMBDA = "lambda"
    ALTERNATIVE = "alternative"
    GAP = "gap"


class NormalizedRoute(BaseModel):
    name: str = ""
    paths: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=lambda: ["GET"])
    hosts: list[str] = Field(default_factory=list)
    strip_path: bool = True
    preserve_host: bool = False
    protocols: list[str] = Field(default_factory=lambda: ["http", "https"])


class NormalizedPlugin(BaseModel):
    name: str
    category: PluginCategory
    scope: str  # "global", "service", "route", "consumer"
    config: dict = Field(default_factory=dict)
    source_plugin_name: str


class NormalizedConsumer(BaseModel):
    username: str
    custom_id: Optional[str] = None
    credentials: list[dict] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)


class NormalizedBackend(BaseModel):
    url: str
    protocol: str = "http"
    connect_timeout: int = 60000
    read_timeout: int = 60000
    write_timeout: int = 60000
    retries: int = 5
    health_checks: Optional[dict] = None
    targets: list[dict] = Field(default_factory=list)


class NormalizedAPI(BaseModel):
    name: str
    backend: NormalizedBackend
    routes: list[NormalizedRoute] = Field(default_factory=list)
    plugins: list[NormalizedPlugin] = Field(default_factory=list)


class NormalizedConfig(BaseModel):
    source_platform: str  # "kong" | "apigee" | "ibm"
    source_version: str = ""
    apis: list[NormalizedAPI] = Field(default_factory=list)
    consumers: list[NormalizedConsumer] = Field(default_factory=list)
    global_plugins: list[NormalizedPlugin] = Field(default_factory=list)
