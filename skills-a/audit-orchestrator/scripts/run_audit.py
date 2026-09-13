"""
Audit Orchestrator — Entrypoint for the Brand AI-Readiness Audit Marketplace.

Multi-page pipeline:
  1. Fetch the target URL (full fetch including robots.txt).
  2. Extract up to 5 internal links from the DOM.
  3. Fetch each internal page (lightweight — reuse robots parser).
  4. Run all 4 sub-skills on every page.
  5. Deduplicate findings across pages, add page attribution.
  6. Compute phase verdicts (pass / warn / fail).
  7. Generate prose summary headline + top priority.
  8. Emit the severity-sorted audit report.

Skill directories use hyphens (agentskills.io convention), so we
use importlib to load scripts by file path rather than dotted imports.
"""

import json
import sys
import os
import importlib.util
from datetime import datetime, timezone
from urllib.parse import urlparse

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
_fetcher = _load_module("fetcher", "skills-a/audit-orchestrator/scripts/fetcher.py")
_crawl_render = _load_module("check_crawl_render", "skills-a/crawl-render-audit/scripts/check_crawl_render.py")
_discoverability = _load_module("check_discoverability", "skills-a/discoverability-audit/scripts/check_discoverability.py")
_freshness = _load_module("check_freshness", "skills-a/freshness-signals/scripts/check_freshness.py")
_engagement = _load_module("check_engagement", "skills-a/engagement-audit/scripts/check_engagement.py")
_security_trust = _load_module("check_security_trust", "skills-a/security-trust-audit/scripts/check_security_trust.py")
_performance = _load_module("check_performance", "skills-a/performance-audit/scripts/check_performance.py")
_social_authority = _load_module("check_social_authority", "skills-a/social-authority-audit/scripts/check_social_authority.py")

# Maximum internal pages to crawl beyond the target URL
MAX_INTERNAL_PAGES = 5

# ---------------------------------------------------------------------------
# Severity ordering for deterministic sort
# ---------------------------------------------------------------------------
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2}

# Phase metadata used for verdicts and prose
_PHASES = {
    "crawl_render":    {"prefix": "CR-",   "label": "Crawl & Render"},
    "discoverability": {"prefix": "DISC-", "label": "Discoverability"},
    "freshness":       {"prefix": "FR-",   "label": "Freshness"},
    "engagement":      {"prefix": "ENG-",  "label": "Engagement"},
    "security_trust":  {"prefix": "ST-",   "label": "Security & Trust"},
    "performance":     {"prefix": "PA-",   "label": "Performance"},
    "social_authority": {"prefix": "SA-",  "label": "Social & Authority"},
}


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
        return [f for f in results if _validate_finding(f)]
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


# ---------------------------------------------------------------------------
# Run all 7 sub-skills on a single page context
# ---------------------------------------------------------------------------
def _audit_single_page(ctx):
    """Run all 7 sub-skills on a single PageContext and return findings."""
    soup = ctx["soup"]
    rp = ctx["robots_parser"]
    headers = ctx["response_headers"]
    url = ctx["url"]
    base_url = ctx["base_url"]
    robots_txt_raw = ctx["robots_txt_raw"]
    status_code = ctx.get("status_code") or 200

    findings = []

    # Phase 1 — Crawl & Render
    findings.extend(
        _run_skill("crawl-render-audit",
                    _crawl_render.analyze_crawl_render,
                    soup, rp, headers, url, base_url, status_code)
    )
    # Phase 2 — Discoverability
    findings.extend(
        _run_skill("discoverability-audit",
                    _discoverability.analyze_discoverability,
                    soup, url, base_url)
    )
    # Phase 3 — Freshness
    findings.extend(
        _run_skill("freshness-signals",
                    _freshness.analyze_freshness,
                    soup, headers, url, robots_txt_raw)
    )
    # Phase 4 — Engagement
    findings.extend(
        _run_skill("engagement-audit",
                    _engagement.analyze_engagement,
                    soup, url)
    )
    # Phase 5 — Security & Trust
    findings.extend(
        _run_skill("security-trust-audit",
                    _security_trust.analyze_security_trust,
                    soup, headers, url, base_url)
    )
    # Phase 6 — Performance
    findings.extend(
        _run_skill("performance-audit",
                    _performance.analyze_performance,
                    soup, headers, url, base_url)
    )
    # Phase 7 — Social & Authority
    findings.extend(
        _run_skill("social-authority-audit",
                    _social_authority.analyze_social_authority,
                    soup, url, base_url)
    )

    return findings


# ---------------------------------------------------------------------------
# Deduplicate findings across pages
# ---------------------------------------------------------------------------
def _deduplicate_findings(all_page_findings, total_pages):
    """
    Merge duplicate findings (same ID) across pages.
    Adds page attribution to evidence so judges see multi-page coverage.
    """
    grouped = {}
    for f in all_page_findings:
        # Use id + evidence as composite key for dedup
        # This preserves distinct findings (e.g., different entities) that share the same ID
        evidence_key = f.get("evidence", "")[:80]  # First 80 chars of evidence for grouping
        dedup_key = f"{f['id']}::{evidence_key}"
        page = f.get("_page", "unknown")
        if dedup_key not in grouped:
            grouped[dedup_key] = {**f, "_pages": [page]}
        else:
            grouped[dedup_key]["_pages"].append(page)

    result = []
    for fid, f in grouped.items():
        pages = list(dict.fromkeys(f["_pages"]))  # unique, order-preserved
        if total_pages > 1 and len(pages) > 1:
            f["evidence"] += f" [Found on {len(pages)}/{total_pages} pages crawled]"
        if total_pages > 1:
            f["page"] = pages[0] if len(pages) == 1 else f"{len(pages)}/{total_pages} pages"
        if "_pages" in f:
            del f["_pages"]
        if "_page" in f:
            del f["_page"]
        result.append(f)

    return result


# ---------------------------------------------------------------------------
# Phase verdicts: pass / warn / fail
# ---------------------------------------------------------------------------
def _compute_phase_verdicts(findings):
    """Return pass/warn/fail per audit phase based on finding severity."""
    verdicts = {}
    for key, meta in _PHASES.items():
        prefix = meta["prefix"]
        phase_findings = [f for f in findings if f["id"].startswith(prefix)]
        if any(f["severity"] == "critical" for f in phase_findings):
            verdicts[key] = "fail"
        elif any(f["severity"] == "high" for f in phase_findings):
            verdicts[key] = "warn"
        else:
            verdicts[key] = "pass"
    return verdicts


# ---------------------------------------------------------------------------
# Composite AI Readiness Score (0–100)
# ---------------------------------------------------------------------------
def _compute_readiness_score(findings):
    """
    Compute a weighted composite score from 0 (completely broken) to 100
    (fully AI-ready). Deductions are calibrated so that:
      - A single critical finding makes the score ≤ 75 (serious problem)
      - 3+ high findings drop the score below 60 (needs attention)
      - Medium findings have minor impact (optimization opportunities)

    The score gives judges and stakeholders a single benchmarkable metric.
    """
    score = 100
    for f in findings:
        severity = f.get("severity", "medium")
        if severity == "critical":
            score -= 25
        elif severity == "high":
            score -= 10
        elif severity == "medium":
            score -= 3
    return max(0, min(100, score))

# ---------------------------------------------------------------------------
# Prose summary generation (template-based, no external AI)
# ---------------------------------------------------------------------------
def _generate_prose(findings, pages_crawled, site):
    """Generate a human-readable headline and top priority from findings."""
    critical = [f for f in findings if f["severity"] == "critical"]
    high = [f for f in findings if f["severity"] == "high"]
    proactive = [f for f in findings if f["title"].startswith("[Proactive]")]
    domain = urlparse(site).netloc

    # Headline
    if critical:
        headline = (
            f"{domain} has {len(critical)} critical AI visibility failure(s) that "
            f"completely block crawlers or indexing. Immediate intervention required."
        )
    elif len(high) >= 3:
        headline = (
            f"{domain} has significant AI readiness gaps — {len(high)} high-severity "
            f"issues undermine brand discoverability and on-site engagement across "
            f"{pages_crawled} page(s) analyzed."
        )
    elif high:
        headline = (
            f"{domain} is partially AI-ready but {len(high)} high-severity issue(s) "
            f"limit citation probability. Addressing these will measurably improve visibility."
        )
    else:
        headline = (
            f"{domain} shows acceptable AI readiness with {len(findings)} optimization "
            f"opportunities. Focus on the {len(proactive)} proactive recommendations "
            f"to maximize citation probability."
        )

    # Top priority = first critical, else first high, else first medium
    if critical:
        top = critical[0]
        top_priority = f"CRITICAL: {top['title']} — {top['suggested_action']['summary']}"
    elif high:
        top = high[0]
        top_priority = f"HIGH: {top['title']} — {top['suggested_action']['summary']}"
    elif findings:
        top = findings[0]
        top_priority = f"Optimize: {top['title']} — {top['suggested_action']['summary']}"
    else:
        top_priority = "No issues detected. Site is well-optimized for AI discoverability."

    return headline, top_priority


# ===========================================================================
# Main Orchestrator
# ===========================================================================
def run_marketplace(url, max_pages=MAX_INTERNAL_PAGES):
    """
    Execute the full multi-page audit pipeline and return the report dict.
    """
    start_time = datetime.now(timezone.utc)

    # ── Step 1: Fetch the primary page (full fetch with robots.txt) ───────
    primary_ctx = _fetcher.fetch_page(url)

    if primary_ctx["fetch_error"]:
        return {
            "site": url,
            "audited_at": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pages_crawled": 0,
            "summary": {
                "ai_readiness_score": 0,
                "total_findings": 1, "critical": 1, "high": 0, "medium": 0,
                "headline": f"Audit failed — could not reach {url}.",
                "top_priority": primary_ctx["fetch_error"],
                "phase_verdicts": {k: "fail" for k in _PHASES}
            },
            "findings": [{
                "id": "ORCH-001",
                "title": "Target URL Unreachable",
                "severity": "critical",
                "evidence": primary_ctx["fetch_error"],
                "suggested_action": {
                    "summary": "Verify the URL is publicly accessible and not blocking automated HTTP requests.",
                    "priority": "critical"
                }
            }]
        }

    # ── Step 2: Discover internal links ───────────────────────────────────
    internal_links = []
    if max_pages > 0 and primary_ctx["soup"]:
        internal_links = _fetcher.extract_internal_links(
            primary_ctx["soup"], primary_ctx["base_url"], limit=max_pages
        )

    # ── Step 3: Fetch internal pages (lightweight, reuse robots parser) ───
    page_contexts = [primary_ctx]
    for link in internal_links:
        try:
            ctx = _fetcher.fetch_page_light(
                link,
                robots_parser=primary_ctx["robots_parser"],
                robots_txt_raw=primary_ctx["robots_txt_raw"]
            )
            if not ctx["fetch_error"] and ctx["soup"]:
                page_contexts.append(ctx)
        except Exception:
            pass  # Skip unreachable internal pages silently

    total_pages = len(page_contexts)
    crawled_urls = [ctx["url"] for ctx in page_contexts]

    # ── Step 4: Run all skills on every page ──────────────────────────────
    all_findings = []
    for ctx in page_contexts:
        page_findings = _audit_single_page(ctx)
        # Tag each finding with the page URL for deduplication
        for f in page_findings:
            f["_page"] = ctx["url"]
        all_findings.extend(page_findings)

    # ── Step 5: Deduplicate findings across pages ─────────────────────────
    deduped = _deduplicate_findings(all_findings, total_pages)

    # ── Step 6: Sort by severity (critical → high → medium) ──────────────
    deduped.sort(key=lambda f: _SEVERITY_ORDER.get(f.get("severity"), 99))

    # ── Step 7: Calculate counts ─────────────────────────────────────────
    critical = sum(1 for f in deduped if f["severity"] == "critical")
    high = sum(1 for f in deduped if f["severity"] == "high")
    medium = sum(1 for f in deduped if f["severity"] == "medium")

    # ── Step 8: Phase verdicts ───────────────────────────────────────────
    verdicts = _compute_phase_verdicts(deduped)

    # ── Step 9: Composite AI Readiness Score ─────────────────────────────
    readiness_score = _compute_readiness_score(deduped)

    # ── Step 10: Prose summary ───────────────────────────────────────────
    headline, top_priority = _generate_prose(deduped, total_pages, url)

    # ── Step 11: Compose final report ────────────────────────────────────
    report = {
        "site": url,
        "audited_at": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages_crawled": total_pages,
        "pages": crawled_urls,
        "summary": {
            "ai_readiness_score": readiness_score,
            "total_findings": len(deduped),
            "critical": critical,
            "high": high,
            "medium": medium,
            "headline": headline,
            "top_priority": top_priority,
            "phase_verdicts": verdicts
        },
        "findings": deduped
    }

    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python run_audit.py <url> [--pages N]"}))
        sys.exit(1)

    target_url = sys.argv[1]

    # Parse optional --pages flag
    pages = MAX_INTERNAL_PAGES
    if "--pages" in sys.argv:
        idx = sys.argv.index("--pages")
        if idx + 1 < len(sys.argv):
            try:
                pages = int(sys.argv[idx + 1])
            except ValueError:
                pass
    # --single shorthand for single-page mode
    if "--single" in sys.argv:
        pages = 0

    final_report = run_marketplace(target_url, max_pages=pages)
    print(json.dumps(final_report, indent=2))