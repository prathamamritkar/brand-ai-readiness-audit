---
name: entity-trust
description: Audit entity identity consistency, brand authority signals, and knowledge-graph trustworthiness across a website's evidence bundle. Use when evaluating whether a brand's machine-readable identity is coherent, authoritative, and resistant to LLM misattribution or hallucination.
license: MIT
compatibility: Python 3.10+, consumes Site Intelligence Evidence Bundle
allowed-tools: Bash(python:*)
---

# Entity Trust

## Purpose

Verify that a brand's entity identity is **consistent, authoritative, and unambiguous** across its web presence. This skill focuses on trust signals that prevent LLMs from misidentifying, conflating, or hallucinating brand attributes.

Unlike `machine-readability` (which reports what structured data exists) and `freshness-corroboration` (which reports temporal signals), `entity-trust` specifically evaluates:

- **Identity coherence** — same brand name, same `@id`, same canonical entity across pages
- **Authority linkage** — `sameAs` links that actually resolve to authoritative nodes
- **Disambiguation strength** — presence of `disambiguatingDescription` and distinct entity boundaries
- **Cross-page consistency** — entity properties that contradict each other across the site

## Input

Consume the **Site Intelligence Evidence Bundle**.

Required evidence:
- Page records with JSON-LD blocks
- Page URLs and canonical URLs
- Robots and sitemap observations

## Procedure

1. **Extract entity nodes** from all JSON-LD blocks on all pages.
2. **Group by entity type** (`Organization`, `Brand`, `Product`, `Person`, etc.).
3. **Check identity coherence**:
   - If the same page contains multiple `Organization`/`Brand` schemas with different names, flag **entity fragmentation**.
   - If `sameAs` URLs are present but do not use known authority domains (`wikidata.org`, `wikipedia.org`, `schema.org`, official social domains), flag **weak authority linkage**.
4. **Check disambiguation**:
   - If `Organization` or `Brand` lacks `disambiguatingDescription`, flag **disambiguation gap**.
5. **Check cross-page consistency**:
   - If two different pages declare `Organization` with different `name` values, flag **identity drift**.
6. **Check `@id` stability**:
   - If the same entity type appears with different `@id` values across pages, flag **unstable entity reference**.
7. Return findings with `category` containing `"entity"`, `"organization"`, `"identity"`, or `"brand"` so downstream correlators can group them into the `entity_identity` family.

## Output

```json
{
  "skill": "entity-trust",
  "schema_version": "entity-trust/v1",
  "findings": [
    {
      "category": "entity identity",
      "issue": "Brand name inconsistent across pages",
      "status": "conflict",
      "page_url": "https://example.com/about",
      "signal": "Organization name 'Acme Inc' on /about vs 'ACME' on /contact",
      "source": "entity trust audit"
    }
  ],
  "limitations": []
}

  
