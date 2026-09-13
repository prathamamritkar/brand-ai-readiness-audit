# Brand AI-Readiness Audit Marketplace

An Agent Skill Marketplace that diagnoses the underlying reasons why a brand is invisible to AI assistants and why human visitors fail to engage. It audits any website — across diverse industry verticals and horizontals — using 57 evidence-backed heuristics covering all failure modes that separate cited brands from ignored ones.

**Recommend-only**: This marketplace strictly audits and reports. No skill ever alters a live site.

## Architecture

The marketplace decomposes the audit into **7 focused domain skills**, each answering a distinct diagnostic question, composed by a single **orchestrator entrypoint**:

```
audit-orchestrator (entrypoint)
  │
  ├─ 1. crawl-render-audit     → "Can AI crawlers reach and extract the content?"
  ├─ 2. discoverability-audit  → "Can AI identify WHO this brand is?"
  ├─ 3. freshness-signals      → "Is the content trustworthy and temporally current?"
  ├─ 4. engagement-audit       → "Will a human visitor stay and engage?"
  ├─ 5. security-trust-audit   → "Does the site signal credibility and trust?"
  ├─ 6. performance-audit      → "Is the page fast and lightweight for crawlers?"
  └─ 7. social-authority-audit → "Does the brand show authoritative social proof?"
```

### Execution Order (Deliberate)
The orchestrator runs skills in strict diagnostic order optimized for AI agent contextual learning:
1. **Crawl & Render** — establishes whether content is even reachable (foundational)
2. **Discoverability** — analyzes structured identity (builds on access)
3. **Freshness** — evaluates temporal trust (builds on identity)
4. **Engagement** — diagnoses human experience (meaningful only if content exists)
5. **Security & Trust** — evaluates credibility signals (builds on all prior context)
6. **Performance** — assesses page weight and load efficiency (affects crawl budget)
7. **Social & Authority** — evaluates social proof and brand authority signals

### Multi-Page Crawl
The orchestrator crawls the target URL **plus up to 5 internal pages** discovered via DOM link extraction. Findings are deduplicated across pages with attribution (e.g., `[Found on 4/6 pages crawled]`). Issues that exist on one specific page show the exact URL.

### Phase Verdicts
Each audit phase receives a verdict: **pass** (no high/critical findings), **warn** (high-severity issues), or **fail** (critical blockers). This gives judges and users an at-a-glance health check.

### AI Readiness Score
Every report includes a **composite AI Readiness Score** (0–100) computed from finding severity: critical (−25), high (−10), medium (−3). This single metric provides a benchmarkable headline number for stakeholders.

### Prose Summary
Every report includes a human-readable `headline` explaining the brand's AI readiness status and a `top_priority` identifying the single most impactful fix.

## Skills

### `audit-orchestrator` (entrypoint)
Orchestrates multi-page crawl, composes the four domain skills, deduplicates findings, computes phase verdicts, calculates the composite AI Readiness Score (0–100), generates prose summary, sorts by severity, and emits the final unified report.

### `crawl-render-audit` (9 heuristics)
Covers: **Crawlability, JS-render gaps, Facts locked in non-text**
- AI crawler blocks via robots.txt (GPTBot, PerplexityBot, ClaudeBot, etc.)
- Meta robots noindex/nosnippet directives
- JS rendering dependency (word count analysis)
- Noscript fallback detection
- SSR framework detection (Next.js, Nuxt, React)
- Facts locked in images without substantive alt text
- Media embeds without text transcripts or VideoObject schema
- Bot-block / CAPTCHA response detection

### `discoverability-audit` (10 heuristics)
Covers: **Missing/invalid structured data, Entity ambiguity**
- JSON-LD presence and syntax validation
- Schema type coverage (generic vs. domain-specific)
- Entity disambiguation via `sameAs` links
- Stable entity anchoring via `@id`
- Canonical URL integrity
- Title, meta description, and Open Graph completeness
- Proactive: hreflang and BreadcrumbList schema

### `freshness-signals` (7 heuristics)
Covers: **Stale or uncorroborated facts**
- Machine-readable date markup (JSON-LD, `<time>`, meta, HTTP headers)
- Stale copyright year detection
- Outdated schema dates (> 2 years)
- Temporal contradiction across date sources
- Author/publisher attribution
- Proactive: FAQ/HowTo schema and sitemap declaration

### `engagement-audit` (10 heuristics)
Covers: **Weak on-site orientation, No context retention**
- Heading hierarchy integrity (h1 presence, level gaps)
- Semantic landmark presence (main, nav, header, footer)
- Lead answer density (front-loaded value proposition)
- Wall-of-text detection and scannability analysis
- Language declaration
- Unlabeled interactive elements
- Proactive: viewport meta tag for mobile

### `security-trust-audit` (7 heuristics)
Covers: **Transport security, Security headers, Trust indicators**
- HTTPS enforcement
- HSTS (Strict-Transport-Security) header
- Content-Security-Policy header
- X-Content-Type-Options and X-Frame-Options headers
- Privacy policy / terms of service page links
- Proactive: Referrer-Policy header

### `performance-audit` (7 heuristics)
Covers: **Page weight, Resource efficiency, Load optimization**
- Excessive external scripts detection
- Render-blocking resources in `<head>`
- Inline HTML and CSS bloat analysis
- Image lazy loading coverage
- Resource hints (preconnect, dns-prefetch, preload)
- Proactive: Web app manifest detection

### `social-authority-audit` (7 heuristics)
Covers: **Social proof, Brand authority, Contact visibility**
- Review/rating structured data (AggregateRating, Review)
- Social media profile links (Twitter, LinkedIn, YouTube, etc.)
- Contact information visibility (email, phone, address)
- Testimonial and case study signals
- About/team page presence
- ContactPoint/LocalBusiness schema
- Proactive: Press/media/awards section detection

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/prathamamritkar/brand-ai-readiness-audit.git
cd brand-ai-readiness-audit
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> Only `requests` + `beautifulsoup4`. No external AI APIs. No headless browsers. No API keys needed.

### 3. Run an audit

```bash
# Full multi-page audit (crawls target + up to 5 internal pages)
python skills-a/audit-orchestrator/scripts/run_audit.py https://example.com

# Limit internal pages crawled
python skills-a/audit-orchestrator/scripts/run_audit.py https://example.com --pages 3

# Single-page mode (fastest)
python skills-a/audit-orchestrator/scripts/run_audit.py https://example.com --single

# Save report to file
python skills-a/audit-orchestrator/scripts/run_audit.py https://example.com > report.json
```

### 4. Run individual skills (optional)

Each sub-skill also works independently:

```bash
python skills-a/crawl-render-audit/scripts/check_crawl_render.py https://example.com
python skills-a/discoverability-audit/scripts/check_discoverability.py https://example.com
python skills-a/freshness-signals/scripts/check_freshness.py https://example.com
python skills-a/engagement-audit/scripts/check_engagement.py https://example.com
python skills-a/security-trust-audit/scripts/check_security_trust.py https://example.com
python skills-a/performance-audit/scripts/check_performance.py https://example.com
python skills-a/social-authority-audit/scripts/check_social_authority.py https://example.com
```

### 5. Run tests

```bash
pip install pytest
pytest tests/ -v
```

## Output Schema

```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-05T08:00:00Z",
  "pages_crawled": 4,
  "pages": ["https://example.com", "https://example.com/about", "..."],
  "summary": {
    "ai_readiness_score": 42,
    "total_findings": 15,
    "critical": 1,
    "high": 6,
    "medium": 8,
    "headline": "example.com has 1 critical AI visibility failure that blocks crawlers.",
    "top_priority": "CRITICAL: Meta Robots Noindex — Remove noindex directive.",
    "phase_verdicts": {
      "crawl_render": "fail",
      "discoverability": "warn",
      "freshness": "pass",
      "engagement": "warn",
      "security_trust": "pass",
      "performance": "pass",
      "social_authority": "warn"
    }
  },
  "findings": [
    {
      "id": "CR-001",
      "title": "AI Crawlers Blocked via robots.txt",
      "severity": "critical",
      "evidence": "AI bots blocked: GPTBot, PerplexityBot. [Found on 4/4 pages crawled]",
      "suggested_action": {
        "summary": "Remove blocks for AI-specific user agents.",
        "priority": "critical"
      },
      "page": "4/4 pages"
    }
  ]
}
```

### AI Readiness Score

Every report includes a **composite AI Readiness Score** (0–100) that provides a single benchmarkable metric:

| Score Range | Interpretation |
|-------------|---------------|
| **90–100** | Excellent — fully optimized for AI crawlers and citations |
| **70–89** | Good — minor optimization opportunities remain |
| **50–69** | Needs Work — significant gaps limiting AI visibility |
| **0–49** | Critical — fundamental failures blocking AI discovery |

Scoring weights: Critical findings deduct 25 points, High deduct 10, Medium deduct 3.

## Testing

```bash
pip install pytest
pytest tests/ -v
```