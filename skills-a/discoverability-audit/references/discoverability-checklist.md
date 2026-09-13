# Discoverability Checklist

This checklist details the heuristics used by the `discoverability-audit` skill to assess how well AI systems can discover, identify, and attribute your brand content.

## Phase A: Structured Data Presence
AI relies heavily on explicitly defined entities. Without structured data, AI has to infer meaning, increasing the risk of hallucinations.

- **DISC-001: No Schema.org Structured Data**
  - **Why it matters:** AI models parse JSON-LD to understand the explicit semantic relationships between content, authors, products, and brands.
  - **Good looks like:** The presence of at least one valid `<script type='application/ld+json'>` block.

- **DISC-002: JSON-LD Syntax Errors**
  - **Why it matters:** Even a small syntax error (like a trailing comma) will silently fail in strict parsers used by bots and AI crawlers.
  - **Good looks like:** 100% valid JSON payload in every schema block.

- **DISC-003: Shallow Schema Type Coverage**
  - **Why it matters:** Simply having `WebSite` or `SearchAction` is insufficient to define business entities. AI needs domain-specific types like `Organization`, `Product`, or `Person` to ground its knowledge graph.
  - **Good looks like:** Meaningful schema types representing the brand and its core offerings.

## Phase B: Entity Disambiguation
Ambiguity is a major failure mode for AI. Disambiguation ensures the brand is identified distinctly from others with the same or similar names.

- **DISC-004: Entity Ambiguity — No sameAs Links**
  - **Why it matters:** AI resolves identity by corroborating across multiple authoritative sources. Missing `sameAs` links prevents disambiguation.
  - **Good looks like:** `sameAs` properties pointing to Wikipedia, Wikidata, LinkedIn, Twitter, Crunchbase, etc.

- **DISC-005: No Stable Entity Anchor (@id)**
  - **Why it matters:** An `@id` property acts as a unique URI within the schema. Without it, entities on different pages remain disconnected.
  - **Good looks like:** Every core entity defined has an absolute or fragment `@id` URI.

- **DISC-006: Missing Canonical URL**
  - **Why it matters:** AI crawlers may encounter content across multiple URL variants (parameters, http/https). Without a canonical tag, attribution leaks.
  - **Good looks like:** `<link rel="canonical" href="https://example.com/...">` present on every page.

## Phase C: SEO Hygiene & Social Signals
Core web metadata acts as primary summarization signals for both traditional search and AI assistants.

- **DISC-007: Missing Title or Meta Description**
  - **Why it matters:** Primary signals for summarizing page content in AI responses.
  - **Good looks like:** Descriptive `<title>` and `<meta name='description'>`.

- **DISC-008: Missing Open Graph Markup**
  - **Why it matters:** Often used as fallbacks by agents for extracting summary content and types.
  - **Good looks like:** Presence of core OG tags (`og:title`, `og:description`, `og:type`, `og:image`).

- **DISC-009: [Proactive] Hreflang Not Declared**
  - **Why it matters:** If the site spans regions, AI might mix up language attribution.
  - **Good looks like:** `<link rel='alternate' hreflang='...'>` used properly for international sites.

- **DISC-010: [Proactive] BreadcrumbList Schema Missing**
  - **Why it matters:** Helps AI construct a structured understanding of site architecture and hierarchy.
  - **Good looks like:** `BreadcrumbList` JSON-LD clearly outlining the path.
