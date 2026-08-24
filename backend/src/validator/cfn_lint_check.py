"""Run cfn-lint against a generated CloudFormation/SAM template.

cfn-lint is used as a library (no CLI, no AWS calls, fully offline). It applies
the SAM transform internally, so ``AWS::Serverless::*`` resources are understood.

Results are advisory only: any failure to import or run cfn-lint returns a
"skipped" result so the validation stage never fails because of linting.
"""

from __future__ import annotations

# cfn-lint encodes severity in the rule id prefix: E=error, W=warning,
# I=informational. We derive the level from that first character.
LEVEL_BY_PREFIX = {"E": "error", "W": "warning", "I": "informational"}

# Cap findings so a pathological template cannot bloat the stored report.
MAX_FINDINGS = 100


def _empty_counts() -> dict:
    return {"error": 0, "warning": 0, "informational": 0}


def _skipped(reason: str) -> dict:
    return {
        "status": "skipped",
        "reason": reason,
        "counts": _empty_counts(),
        "findings": [],
        "truncated": False,
    }


def lint_template(template_str: str) -> dict:
    """Lint a template string and return a structured, JSON-serializable result.

    Returns a dict with:
        status: "pass" | "fail" | "skipped"
        counts: {error, warning, informational}
        findings: [{id, level, message, line}]
        truncated: bool  (True when findings were capped)
        reason: str      (present only when skipped)
    """
    try:
        from cfnlint import api
    except Exception as exc:  # layer missing or import failure
        return _skipped(f"cfn-lint unavailable: {exc}")

    try:
        matches = api.lint_all(template_str)
    except Exception as exc:
        return _skipped(f"cfn-lint execution failed: {exc}")

    counts = _empty_counts()
    findings: list[dict] = []

    for match in matches:
        rule_id = getattr(getattr(match, "rule", None), "id", "") or ""
        level = LEVEL_BY_PREFIX.get(rule_id[:1], "error")
        counts[level] = counts.get(level, 0) + 1

        if len(findings) < MAX_FINDINGS:
            findings.append(
                {
                    "id": rule_id,
                    "level": level,
                    "message": getattr(match, "message", ""),
                    "line": getattr(match, "linenumber", None),
                }
            )

    total = counts["error"] + counts["warning"] + counts["informational"]
    return {
        "status": "fail" if counts["error"] > 0 else "pass",
        "counts": counts,
        "findings": findings,
        "truncated": total > len(findings),
    }
