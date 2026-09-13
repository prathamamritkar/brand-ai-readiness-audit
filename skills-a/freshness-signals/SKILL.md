---
name: freshness-signals
description: Evaluates temporal trust signals, freshness corroboration, and author attribution on web pages to determine AI-readiness. AI models increasingly weigh recency and factual freshness when answering user queries. This skill analyzes machine-readable dates, schema declarations, author attribution, copyright staleness, and corroborating signals like robots.txt sitemaps to ensure content is treated as trustworthy and current.
license: Apache-2.0
---

# Freshness Signals Skill

**When to use:** Use this skill to determine if AI agents and LLMs will perceive a brand's content as up-to-date, corroborated, and authoritative, or if it will be treated as stale and untrustworthy.

## Inputs
- `url` (string): The URL of the page to analyze.
- `soup` (BeautifulSoup): Pre-fetched DOM (for function mode).
- `response_headers` (dict): HTTP response headers.
- `robots_txt_raw` (string): Raw contents of robots.txt for Sitemap check.

## Procedure

### Phase A — Temporal Markers
1. **Machine-Readable Date Markup:** Check JSON-LD, `<time>` tags, date-related `<meta>` tags, and `Last-Modified` HTTP header for explicit dates.
2. **Stale Copyright Year:** Extract copyright years using regex in the footer or page text, and compare them against the current year.
3. **Outdated Schema Dates:** Parse structured data (JSON-LD) for `datePublished` and `dateModified`. Check if they are older than 2 years.
4. **Temporal Contradiction:** Compare dates across copyright, schema, and HTML tags to detect conflicting timestamps.

### Phase B — Corroboration Signals
5. **Author or Publisher Attribution:** Ensure explicit author or publisher fields exist in JSON-LD or meta tags to establish authority.
6. **[Proactive] FAQ or HowTo Schema:** Check for high-value AI schemas (FAQPage, HowTo) that improve citation likelihood.
7. **[Proactive] Sitemap in robots.txt:** Verify `Sitemap:` directive exists in `robots.txt` to guide AI crawlers to recent content.

## Output Format
Outputs a JSON array of findings. Each finding follows the standard schema:
```json
{
  "id": "PREFIX-NNN",
  "title": "Issue Title",
  "severity": "critical|high|medium",
  "evidence": "Concrete proof from DOM",
  "suggested_action": {
    "summary": "Specific fix with mechanism explanation",
    "priority": "critical|high|medium"
  }
}
```
