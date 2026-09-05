---
name: discoverability-audit
description: Evaluates a brand's discoverability for AI systems by analyzing structured data validation, entity disambiguation, and SEO hygiene signals. This skill ensures that AI engines can correctly identify the brand, parse the entities present on the page, and resolve ambiguities using valid JSON-LD schemas, authoritative sameAs links, canonical URLs, and core metadata elements.
license: Apache-2.0
---

# Discoverability Audit Skill

## When to Use
Use this skill to determine if AI systems can correctly identify WHO a brand is and properly attribute their content. This is essential when assessing whether brand ambiguity or missing structured data might prevent AI models from accurately retrieving and citing the brand.

## Inputs
- `url`: The target URL to analyze.

## Procedure
The audit is divided into three phases:

1. **Phase A — Structured Data Presence:** Validates the existence and syntactic correctness of JSON-LD blocks, and checks for domain-specific schema types.
2. **Phase B — Entity Disambiguation:** Checks for authoritative `sameAs` links, stable `@id` anchors, and valid canonical URLs to ensure the entity is distinctly identifiable.
3. **Phase C — SEO Hygiene & Social Signals:** Verifies core metadata, Open Graph tags, and proactive signals like hreflang and BreadcrumbList schemas.

## Output Format
The output is a JSON array containing findings for the audited page. Each finding adheres to the standard schema:
- `id`: The issue identifier (e.g., DISC-001)
- `title`: A brief title of the issue
- `severity`: high, medium, or critical
- `evidence`: Concrete proof derived from the DOM
- `suggested_action`: A dictionary containing `summary` (with a mechanism explanation) and `priority`.

For detailed checks, refer to the [Discoverability Checklist](references/discoverability-checklist.md).