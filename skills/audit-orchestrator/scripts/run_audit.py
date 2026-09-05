"""
Audit Orchestrator — Entrypoint for the Brand AI-Readiness Audit Marketplace.

Fetches the target URL exactly once, then runs four sub-skills in strict
diagnostic order and composes the final severity-sorted audit report.

Note: Skill directories use hyphens (agentskills.io convention), so we
use importlib to load scripts by file path rather than dotted module imports.
"""

import json
import sys
import os
import importlib.util
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Resolve the repository root so we can locate skill scripts by path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))


def _load_module(name, rel_path):
    """Load a Python module from a file path relative to the repo root."""
    abs_path = os.path.join(_REPO_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Lazy-load sub-skill modules by file path (handles hyphenated dirs)
# ---------------------------------------------------------------------------
_fetcher = _load_module("fetcher", "skills/utils/fetcher.py")
_crawl_render = _load_module("check_crawl_render", "skills/crawl-render-audit/scripts/check_crawl_render.py")
_discoverability = _load_module("check_discoverability", "skills/discoverability-audit/scripts/check_discoverability.py")
_freshness = _load_module("check_freshness", "skills/freshness-signals/scripts/check_freshness.py")
_engagement = _load_module("check_engagement", "skills/engagement-audit/scripts/check_engagement.py")


# ---------------------------------------------------------------------------
# Severity ordering for deterministic sort
# ---------------------------------------------------------------------------
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


def _validate_finding(f):
    """Ensure a finding dict has all mandatory fields."""
    required = {"id", "title", "severity", "evidence", "suggested_action"}
    if not isinstance(f, dict):
        return False
    if not required.issubset(f.keys()):
        return False
    if f.get("severity") not in _SEVERITY_ORDER:
        return False
    sa = f.get("suggested_action", {})
    if not isinstance(sa, dict) or "summary" not in sa or "priority" not in sa:
        return False
    return True


def _run_skill(name, fn, *args, **kwargs):
    """Run a sub-skill safely; return findings list or an error finding."""
    try:
        results = fn(*args, **kwargs)
        if not isinstance(results, list):
            results = [results] if isinstance(results, dict) else []
        # Validate each finding
        valid = [f for f in results if _validate_finding(f)]
        return valid
    except Exception as e:
        return [{
            "id": f"{name}-ERR",
            "title": f"{name} Execution Failure",
            "severity": "critical",
            "evidence": f"Sub-skill '{name}' raised an exception: {str(e)}",
            "suggested_action": {
                "summary": f"Investigate why the {name} skill failed. This may indicate an unusual DOM structure.",
                "priority": "critical"
            }
        }]


def run_marketplace(url):
    """
    Execute the full audit pipeline and return the final report dict.
    """
    # ── Step 1: Single Fetch ──────────────────────────────────────────────
    ctx = _fetcher.fetch_page(url)

    if ctx["fetch_error"]:
        return {
            "site": url,
            "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": {"total_findings": 1, "critical": 1, "high": 0, "medium": 0},
            "findings": [{
                "id": "ORCH-001",
                "title": "Target URL Unreachable",
                "severity": "critical",
                "evidence": ctx["fetch_error"],
                "suggested_action": {
                    "summary": "Verify the URL is publicly accessible and not blocking automated HTTP requests.",
                    "priority": "critical"
                }
            }]
        }

    soup = ctx["soup"]
    rp = ctx["robots_parser"]
    headers = ctx["response_headers"]
    base_url = ctx["base_url"]
    robots_txt_raw = ctx["robots_txt_raw"]

    # ── Step 2: Execute sub-skills in strict diagnostic order ─────────────
    #
    # The order is deliberate and optimized for AI agent contextual learning:
    #   1. Crawl-Render  — Can AI reach the content?        (foundational)
    #   2. Discoverability — Can AI identify the brand?     (builds on access)
    #   3. Freshness      — Can AI trust the content?       (builds on identity)
    #   4. Engagement     — Will humans stay?               (meaningful only if content exists)
    #
    all_findings = []

    # Phase 1 — Crawl & Render
    all_findings.extend(
        _run_skill("crawl-render-audit",
                    _crawl_render.analyze_crawl_render,
                    soup, rp, headers, url, base_url)
    )

    # Phase 2 — Discoverability
    all_findings.extend(
        _run_skill("discoverability-audit",
                    _discoverability.analyze_discoverability,
                    soup, url, base_url)
    )

    # Phase 3 — Freshness
    all_findings.extend(
        _run_skill("freshness-signals",
                    _freshness.analyze_freshness,
                    soup, headers, url, robots_txt_raw)
    )

    # Phase 4 — Engagement
    all_findings.extend(
        _run_skill("engagement-audit",
                    _engagement.analyze_engagement,
                    soup, url)
    )

    # ── Step 3: Sort findings by severity (critical → high → medium) ─────
    all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.get("severity"), 99))

    # ── Step 4: Calculate summary ────────────────────────────────────────
    critical = sum(1 for f in all_findings if f["severity"] == "critical")
    high = sum(1 for f in all_findings if f["severity"] == "high")
    medium = sum(1 for f in all_findings if f["severity"] == "medium")

    report = {
        "site": url,
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_findings": len(all_findings),
            "critical": critical,
            "high": high,
            "medium": medium
        },
        "findings": all_findings
    }

    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python run_audit.py <url>"}))
        sys.exit(1)

    target_url = sys.argv[1]
    final_report = run_marketplace(target_url)
    print(json.dumps(final_report, indent=2))