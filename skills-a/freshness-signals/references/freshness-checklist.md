# Freshness Signals Reference Checklist

## Why Freshness Matters to AI
Generative AI models and LLM agents heavily rely on **temporal markers** to decide if content is current, trustworthy, or deprecated. Without clear dates and active corroborating signals, AI assumes information may be stale, causing it to fall out of citations in preference of well-timestamped competitors.

## Phase A: Temporal Markers

### FR-001: Machine-Readable Date Markup
**What good looks like:**
- A clear `dateModified` in `application/ld+json` (Schema.org).
- `<time datetime="...">` tags for user-visible dates.
- Standard meta tags (`article:modified_time`).
- HTTP `Last-Modified` headers.

### FR-002: Stale Copyright Year
**What good looks like:**
- Copyright year dynamically updates to the current year.
- AI interprets a stale footer as a proxy for an abandoned domain.

### FR-003: Outdated Schema Dates
**What good looks like:**
- Dates within JSON-LD should be refreshed. Anything >2 years old may trigger "recency bias" deprioritization.

### FR-004: Temporal Contradiction
**What good looks like:**
- Synchronized dates across all sources. E.g., if JSON-LD says updated in 2025, but the footer says 2021, AI will treat the freshness signal as noisy and untrustworthy.

## Phase B: Corroboration Signals

### FR-005: Author or Publisher Attribution
**What good looks like:**
- Explicit `author` or `publisher` JSON-LD schemas. Without an entity taking responsibility for the content, AI may discount its authority.

### FR-006: [Proactive] No FAQ or HowTo Schema
**What good looks like:**
- Inclusion of structured schemas highly favored by AI. `FAQPage` and `HowTo` directly feed generative answers in LLMs.

### FR-007: [Proactive] Sitemap Not Declared in robots.txt
**What good looks like:**
- A `Sitemap: https://...` directive in the robots.txt file. Rapid AI crawling depends on XML sitemaps to find updated URLs efficiently.
