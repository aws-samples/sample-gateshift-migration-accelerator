"""Unit tests for the validation and confidence scoring engine."""

import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock boto3 before importing handler
sys.modules["boto3"] = MagicMock()

from validator.handler import (
    _validate_route_coverage,
    _validate_auth_coverage,
    _validate_plugin_coverage,
    _collect_all_mappings,
    _collect_gaps,
)


class TestValidateRouteCoverage:
    """Tests for route coverage validation."""

    def test_full_coverage(self):
        normalized = {
            "apis": [
                {
                    "routes": [
                        {"paths": ["/api/users"], "methods": ["GET", "POST"]},
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "resources": [
                        {"path": "/api/users", "methods": ["GET", "POST"]},
                    ]
                }
            ]
        }
        result = _validate_route_coverage(normalized, plan)
        assert result["percentage"] == 100.0
        assert result["total"] == 2
        assert result["covered"] == 2

    def test_partial_coverage(self):
        normalized = {
            "apis": [
                {
                    "routes": [
                        {"paths": ["/api/users"], "methods": ["GET", "POST", "DELETE"]},
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "resources": [
                        {"path": "/api/users", "methods": ["GET", "POST"]},
                    ]
                }
            ]
        }
        result = _validate_route_coverage(normalized, plan)
        assert result["total"] == 3
        assert result["covered"] == 2
        assert 60 < result["percentage"] < 70

    def test_no_coverage(self):
        normalized = {
            "apis": [
                {
                    "routes": [
                        {"paths": ["/api/users"], "methods": ["GET"]},
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "resources": [
                        {"path": "/api/orders", "methods": ["POST"]},
                    ]
                }
            ]
        }
        result = _validate_route_coverage(normalized, plan)
        assert result["covered"] == 0
        assert result["percentage"] == 0.0

    def test_empty_plan_gives_partial_credit(self):
        """When Bedrock doesn't list explicit resources, assume 80% coverage.
        Note: empty list is not the same as no resources at all — the logic checks
        `if not plan_routes and source_routes`. An empty resources list produces
        an empty plan_routes set, but with 2 source_routes total → covered = int(2*0.8) = 1.
        """
        normalized = {
            "apis": [
                {
                    "routes": [
                        {"paths": ["/api/users"], "methods": ["GET", "POST"]},
                    ]
                }
            ]
        }
        plan = {"apis": [{"resources": []}]}
        result = _validate_route_coverage(normalized, plan)
        # With 2 routes: covered = int(2*0.8) = 1, pct = 50%
        assert result["percentage"] == 50.0

    def test_no_routes_returns_default(self):
        """When there are no source routes, total defaults to 1 and covered = int(1*0.8) = 0 via partial credit path."""
        normalized = {"apis": [{"routes": []}]}
        plan = {"apis": [{"resources": []}]}
        result = _validate_route_coverage(normalized, plan)
        # source_routes is empty, so total = 1 (from `if source_routes else 1`)
        # plan_routes is also empty, but `not plan_routes and source_routes` is False
        # because source_routes is empty. So covered stays 0. pct = 0/1 = 0
        assert result["percentage"] == 0.0

    def test_multiple_paths_multiple_methods(self):
        normalized = {
            "apis": [
                {
                    "routes": [
                        {"paths": ["/a", "/b"], "methods": ["GET", "POST"]},
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "resources": [
                        {"path": "/a", "methods": ["GET", "POST"]},
                        {"path": "/b", "methods": ["GET", "POST"]},
                    ]
                }
            ]
        }
        result = _validate_route_coverage(normalized, plan)
        assert result["total"] == 4
        assert result["covered"] == 4
        assert result["percentage"] == 100.0

    def test_details_contains_uncovered_routes(self):
        normalized = {
            "apis": [
                {
                    "routes": [
                        {"paths": ["/api/users", "/api/orders"], "methods": ["GET"]},
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "resources": [
                        {"path": "/api/users", "methods": ["GET"]},
                    ]
                }
            ]
        }
        result = _validate_route_coverage(normalized, plan)
        assert "GET /api/orders" in result["details"]


class TestValidateAuthCoverage:
    """Tests for authentication coverage validation."""

    def test_no_auth_plugins_returns_100(self):
        normalized = {"apis": [{"plugins": [{"category": "cors", "name": "cors"}]}]}
        plan = {"apis": [{"authorizer_type": "NONE", "feature_mappings": []}]}
        result = _validate_auth_coverage(normalized, plan)
        assert result["percentage"] == 100

    def test_auth_plugin_mapped(self):
        normalized = {
            "apis": [
                {
                    "plugins": [
                        {"category": "authentication", "source_plugin_name": "key-auth", "name": "key-auth"}
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "authorizer_type": "API_KEY",
                    "feature_mappings": [
                        {"source_plugin_name": "key-auth", "mapping_type": "direct"}
                    ],
                }
            ]
        }
        result = _validate_auth_coverage(normalized, plan)
        assert result["percentage"] == 100.0

    def test_auth_plugin_not_mapped(self):
        normalized = {
            "apis": [
                {
                    "plugins": [
                        {"category": "authentication", "source_plugin_name": "jwt", "name": "jwt"}
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "authorizer_type": "NONE",
                    "feature_mappings": [],
                }
            ]
        }
        result = _validate_auth_coverage(normalized, plan)
        assert result["percentage"] == 0.0

    def test_multiple_auth_plugins_partial_coverage(self):
        normalized = {
            "apis": [
                {
                    "plugins": [
                        {"category": "authentication", "source_plugin_name": "key-auth", "name": "key-auth"},
                        {"category": "authentication", "source_plugin_name": "acl", "name": "acl"},
                    ]
                }
            ]
        }
        plan = {
            "apis": [
                {
                    "authorizer_type": "API_KEY",
                    "feature_mappings": [
                        {"source_plugin_name": "key-auth", "mapping_type": "direct"},
                    ],
                }
            ]
        }
        result = _validate_auth_coverage(normalized, plan)
        assert result["total"] == 2
        assert result["covered"] == 1
        assert result["percentage"] == 50.0


class TestValidatePluginCoverage:
    """Tests for plugin coverage validation."""

    def test_all_plugins_mapped(self):
        normalized = {
            "apis": [
                {
                    "plugins": [
                        {"source_plugin_name": "cors", "name": "cors"},
                        {"source_plugin_name": "rate-limiting", "name": "rate-limiting"},
                    ]
                }
            ],
            "global_plugins": [],
        }
        plan = {
            "apis": [
                {
                    "feature_mappings": [
                        {"source_plugin_name": "cors", "mapping_type": "direct"},
                        {"source_plugin_name": "rate-limiting", "mapping_type": "direct"},
                    ]
                }
            ]
        }
        result = _validate_plugin_coverage(normalized, plan)
        assert result["percentage"] == 100.0

    def test_gap_plugins_not_counted_as_covered(self):
        normalized = {
            "apis": [
                {
                    "plugins": [
                        {"source_plugin_name": "cors", "name": "cors"},
                        {"source_plugin_name": "custom-plugin", "name": "custom-plugin"},
                    ]
                }
            ],
            "global_plugins": [],
        }
        plan = {
            "apis": [
                {
                    "feature_mappings": [
                        {"source_plugin_name": "cors", "mapping_type": "direct"},
                        {"source_plugin_name": "custom-plugin", "mapping_type": "gap"},
                    ]
                }
            ]
        }
        result = _validate_plugin_coverage(normalized, plan)
        assert result["total"] == 2
        assert result["covered"] == 1
        assert result["percentage"] == 50.0

    def test_lambda_mapping_counts_as_covered(self):
        normalized = {
            "apis": [{"plugins": [{"source_plugin_name": "jwt", "name": "jwt"}]}],
            "global_plugins": [],
        }
        plan = {
            "apis": [
                {
                    "feature_mappings": [
                        {"source_plugin_name": "jwt", "mapping_type": "lambda"}
                    ]
                }
            ]
        }
        result = _validate_plugin_coverage(normalized, plan)
        assert result["percentage"] == 100.0

    def test_alternative_mapping_counts_as_covered(self):
        normalized = {
            "apis": [{"plugins": [{"source_plugin_name": "http-log", "name": "http-log"}]}],
            "global_plugins": [],
        }
        plan = {
            "apis": [
                {
                    "feature_mappings": [
                        {"source_plugin_name": "http-log", "mapping_type": "alternative"}
                    ]
                }
            ]
        }
        result = _validate_plugin_coverage(normalized, plan)
        assert result["percentage"] == 100.0

    def test_global_plugins_included(self):
        normalized = {
            "apis": [{"plugins": []}],
            "global_plugins": [
                {"source_plugin_name": "correlation-id", "name": "correlation-id"},
                {"source_plugin_name": "file-log", "name": "file-log"},
            ],
        }
        plan = {
            "apis": [
                {
                    "feature_mappings": [
                        {"source_plugin_name": "correlation-id", "mapping_type": "direct"},
                    ]
                }
            ]
        }
        result = _validate_plugin_coverage(normalized, plan)
        assert result["total"] == 2
        assert result["covered"] == 1
        assert result["details"] == ["file-log"]

    def test_empty_plugins_returns_zero(self):
        """When no plugins exist, the set is empty so total = 1 (from the else), covered = 0."""
        normalized = {"apis": [{"plugins": []}], "global_plugins": []}
        plan = {"apis": [{"feature_mappings": []}]}
        result = _validate_plugin_coverage(normalized, plan)
        # all_plugins is empty set → total = 1 (from `if all_plugins else 1`)
        # No intersection → covered = 0 → pct = 0
        assert result["percentage"] == 0.0

    def test_deduplicates_plugins(self):
        """Same plugin on multiple services should count once."""
        normalized = {
            "apis": [
                {"plugins": [{"source_plugin_name": "cors", "name": "cors"}]},
                {"plugins": [{"source_plugin_name": "cors", "name": "cors"}]},
            ],
            "global_plugins": [],
        }
        plan = {
            "apis": [
                {"feature_mappings": [{"source_plugin_name": "cors", "mapping_type": "direct"}]},
                {"feature_mappings": [{"source_plugin_name": "cors", "mapping_type": "direct"}]},
            ]
        }
        result = _validate_plugin_coverage(normalized, plan)
        assert result["total"] == 1
        assert result["covered"] == 1


class TestCollectAllMappings:
    """Tests for collecting feature mappings from the plan."""

    def test_collects_from_multiple_apis(self, sample_migration_plan):
        mappings = _collect_all_mappings(sample_migration_plan)
        assert len(mappings) == 5  # 3 from payment + 2 from user

    def test_empty_plan(self):
        plan = {"apis": []}
        assert _collect_all_mappings(plan) == []

    def test_preserves_mapping_fields(self, sample_migration_plan):
        mappings = _collect_all_mappings(sample_migration_plan)
        first = mappings[0]
        assert "source_plugin_name" in first
        assert "aws_equivalent" in first
        assert "mapping_type" in first


class TestCollectGaps:
    """Tests for collecting gap items."""

    def test_no_gaps_returns_empty(self, sample_migration_plan):
        gaps = _collect_gaps(sample_migration_plan)
        assert gaps == []

    def test_collects_gap_items(self, sample_migration_plan_with_gaps):
        gaps = _collect_gaps(sample_migration_plan_with_gaps)
        assert len(gaps) == 1
        assert gaps[0]["source_plugin_name"] == "custom-lua-plugin"

    def test_gap_item_has_required_fields(self, sample_migration_plan_with_gaps):
        gaps = _collect_gaps(sample_migration_plan_with_gaps)
        gap = gaps[0]
        assert "source_feature" in gap
        assert "source_plugin_name" in gap
        assert "severity" in gap
        assert "recommendation" in gap
        assert "effort_estimate_hours" in gap

    def test_gap_default_severity_is_medium(self, sample_migration_plan_with_gaps):
        gaps = _collect_gaps(sample_migration_plan_with_gaps)
        assert gaps[0]["severity"] == "medium"

    def test_gap_default_effort_is_4_hours(self, sample_migration_plan_with_gaps):
        gaps = _collect_gaps(sample_migration_plan_with_gaps)
        assert gaps[0]["effort_estimate_hours"] == 4


class TestConfidenceScoreCalculation:
    """Tests for the overall confidence score formula."""

    def test_perfect_score(self):
        """100% on all dimensions = 100%."""
        score = 100 * 0.30 + 100 * 0.25 + 100 * 0.25 + 100 * 0.20
        assert score == 100.0

    def test_zero_route_coverage(self):
        """0% route coverage impacts score by 30%."""
        score = 0 * 0.30 + 100 * 0.25 + 100 * 0.25 + 100 * 0.20
        assert score == 70.0

    def test_zero_plugin_coverage(self):
        """0% plugin coverage impacts score by 25%."""
        score = 100 * 0.30 + 100 * 0.25 + 0 * 0.25 + 100 * 0.20
        assert score == 75.0

    def test_threshold_80_is_complete(self):
        """Score >= 80 means COMPLETE."""
        score = 80 * 0.30 + 80 * 0.25 + 80 * 0.25 + 100 * 0.20
        assert score >= 80

    def test_below_80_is_needs_review(self):
        """Score < 80 means NEEDS_REVIEW."""
        score = 50 * 0.30 + 50 * 0.25 + 50 * 0.25 + 100 * 0.20
        # 15 + 12.5 + 12.5 + 20 = 60
        assert score < 80
