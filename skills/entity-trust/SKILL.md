---
name: entity-trust
description: Evaluate whether a website provides clear, consistent, and machine-interpretable identity signals for its organization, products, or services. Use when auditing entity clarity and trust signals from collected page evidence.
license: Apache-2.0
metadata:
  entrypoint: false
  version: 3.0.0
allowed-tools:
  - python-runtime
---

# Entity Trust

## Purpose

The Entity Trust skill evaluates how clearly a website establishes and represents its core entities.

It looks for evidence that helps an automated system understand:

- Who operates the website
- What organization or brand is represented
- What products or services are offered
- How important entities are named and described
- Whether identity information is consistent across relevant pages
- Whether machine-readable entity references reinforce visible identity

The skill evaluates observable website evidence only. It does not determine real-world reputation, legal validity, popularity, or external trust.

Unlike machine-readability, which reports structured-data presence, this skill evaluates whether identity signals are coherent and understandable across the available evidence.

## Inputs

The skill consumes Site Intelligence evidence, including:

- Page URL
- Page type
- Title
- Meta description
- Visible text
- Headings
- Canonical URL
- JSON-LD blocks
- Links
- Language
- Site-level crawl metadata

The skill must tolerate missing fields.

## Core Principles

### 1. Observable evidence only

Evaluate information actually present in the supplied evidence.

Do not infer ownership, authority, popularity, legitimacy, or reputation from unsupported assumptions.

### 2. Entity clarity

A useful website should provide enough consistent information to establish its primary organization, brand, product, or service entities.

### 3. Cross-page consistency

Identity signals should be compared across relevant pages when evidence is available.

Do not treat missing evidence on one page as proof that the entire site lacks the signal.

### 4. Machine interpretation

Human-readable identity information and machine-readable identity information should reinforce each other.

Relevant machine-readable evidence may include JSON-LD organization, brand, product, service, website, or related entity representations.

### 5. Entity references

When JSON-LD contains entity identifiers such as `@id`, evaluate whether the same apparent entity uses a stable identifier across relevant pages.

Do not assume that different identifiers are automatically incorrect; report instability only when the available evidence indicates that they represent the same entity.

### 6. Relationship signals

Evaluate observable relationships between:

- Organization → website
- Organization → products/services
- Product/service → relevant page
- Brand → offering

Structured relationships such as `@id`, `url`, `brand`, `manufacturer`, or `provider` may provide supporting evidence when present.

### 7. Context matters

A missing organization name on a product page may be acceptable when site-level evidence clearly establishes the organization elsewhere.

Findings should therefore use the smallest useful scope.

### 8. No external reputation claims

The skill must not use:

- Search engine rankings
- Social media popularity
- Third-party reviews
- External backlinks
- External reputation databases

unless such evidence is explicitly supplied as an input.

## Identity Signals

### Organization identity

Look for:

- Organization or brand name
- About/company information
- Contact information
- Consistent naming
- Organization-related structured data (`@type: Organization` or `Brand`)
- Stable entity identifiers where available
- `disambiguatingDescription` field in Organization/Brand JSON-LD — if visible identity exists but `disambiguatingDescription` is absent → flag `medium`. Evidence: report which pages have Organization/Brand JSON-LD and whether the field was present. Scope: `brand`. (Note: `sameAs` presence is audited by `freshness-corroboration`; this skill audits whether the description disambiguates the brand from similarly-named entities.)
- Useful disambiguating descriptions where available

### Product or service identity

Look for:

- Clear product/service name
- Description
- Relevant category or purpose
- Consistent naming across pages
- Product/service structured data where appropriate
- Observable relationship to the organization or brand

### Relationship signals

Look for evidence connecting:

- Organization → website
- Organization → products/services
- Product/service → relevant page
- Brand → offering

### Consistency signals

Compare relevant pages for:

- Organization or brand naming
- Product/service naming
- Descriptions
- Canonical identity
- Structured data versus visible content
- `@id` stability
- Entity relationships

## Finding Rules

The skill should produce findings only when evidence supports them.

### Missing organization identity

If relevant site evidence lacks a clear organization or brand identity:

- Signal: `organization_identity_unclear`
- Status: `absent`

### Missing product/service identity

If a product or service page does not clearly establish what is being offered:

- Signal: `offering_identity_unclear`
- Status: `absent`

### Identity inconsistency

If relevant pages provide materially different organization, brand, product, or service naming:

- Signal: `identity_inconsistency`
- Status: `present`

### Machine-readable identity gap

If visible identity information exists but relevant machine-readable entity representation is absent:

- Signal: `machine_identity_gap`
- Status: `absent`

### Unstable entity reference

If the same apparent entity is represented with materially different `@id` values across relevant pages:

- Signal: `unstable_entity_reference`
- Status: `present`

Only report this when available evidence supports that the identifiers refer to the same entity.

### Entity relationship gap

If an offering is clearly associated with an organization or brand in visible content but the available machine-readable evidence does not expose a corresponding relationship:

- Signal: `entity_relationship_gap`
- Status: `absent`

Only report this when the relationship is observable from the supplied evidence.

### Consistent identity

If relevant identity evidence is clear and consistent:

- Signal: `entity_identity_clear`
- Status: `present`

## Confidence

Confidence reflects evidence quality, not business importance.

Use:

- `high` when multiple independent page signals support the observation
- `medium` when a clear signal exists from limited evidence
- `low` when evidence is incomplete or ambiguous

## Output Schema

Each finding must conform to the marketplace standard shape:

```json
{
  "id": "ET-001",
  "title": "Organization Identity Unclear Across Site",
  "severity": "high",
  "gap_type": "citation",
  "category": "entity_identity",
  "url": "https://example.com",
  "evidence": "No Organization or Brand JSON-LD found on homepage or about page. Title present but no machine-readable identity.",
  "suggested_action": {
    "summary": "Add Organization JSON-LD with name, url, logo, sameAs, and disambiguatingDescription to the homepage.",
    "priority": "high",
    "scope": "site"
  }
}
```

### Severity mapping

| Signal | `confidence` | → `severity` |
|---|---|---|
| `organization_identity_unclear` | high/medium | `high` |
| `machine_identity_gap` | medium | `high` |
| `offering_identity_unclear` | medium | `medium` |
| `identity_inconsistency` | medium | `medium` |
| `unstable_entity_reference` | high | `high`, medium → `medium` |
| `entity_relationship_gap` | medium | `medium` |
| `missing_disambiguating_description` | medium | `medium` |
| `entity_identity_clear` | any | omit — positive signal, do not emit as a finding |

### `suggested_action` catalog per signal

| Signal | `suggested_action.summary` |
|---|---|
| `organization_identity_unclear` | Add `Organization` JSON-LD with `name`, `url`, `logo`, `sameAs`, and `disambiguatingDescription` to the homepage and about page. |
| `machine_identity_gap` | Visible brand identity exists but no machine-readable equivalent. Add `Organization` JSON-LD to expose identity to AI extractors. |
| `offering_identity_unclear` | Add `Product` or `Service` JSON-LD with `name`, `description`, and `category` to each offering page. |
| `identity_inconsistency` | Normalize brand and product names across all pages and structured data blocks to eliminate entity conflation risk. |
| `unstable_entity_reference` | Use a single stable `@id` URL (e.g. `https://example.com/#organization`) across all Organization JSON-LD blocks. |
| `entity_relationship_gap` | Add explicit `brand`, `manufacturer`, or `provider` relationships in JSON-LD to link offerings to the parent Organization. |
| `missing_disambiguating_description` | Add `disambiguatingDescription` to Organization/Brand JSON-LD (e.g. "Acme Inc. is a B2B SaaS company focused on supply-chain analytics, distinct from Acme Corp. the hardware retailer."). |