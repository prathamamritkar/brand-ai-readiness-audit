---
name: entity-trust
description: Evaluate whether a website provides clear, consistent, and machine-interpretable identity signals for its organization, products, or services. Use when auditing entity clarity and trust signals from collected page evidence.
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

The skill evaluates observable website evidence only. It does not determine real-world reputation, legal validity, popularity, or external trust.

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

Relevant machine-readable evidence may include JSON-LD organization, product, service, website, or related entity representations.

### 5. Context matters

A missing organization name on a product page may be acceptable when the site-level evidence clearly establishes the organization elsewhere.

Findings should therefore use the smallest useful scope.

### 6. No external reputation claims

The skill must not use:

- Search engine rankings
- Social media popularity
- Third-party reviews
- External backlinks
- External reputation databases

unless such evidence is explicitly supplied as an input.

## Identity Signals

Evaluate available evidence for:

### Organization identity

Look for:

- Organization or brand name
- About/company information
- Contact information
- Consistent naming
- Organization-related structured data

### Product or service identity

Look for:

- Clear product/service name
- Description
- Relevant category or purpose
- Consistent naming across pages
- Product/service structured data where appropriate

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

## Finding Rules

The skill should produce findings only when evidence supports them.

Examples:

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

Return:

```json
{
  "schema_version": "entity-trust/v1",
  "summary": {
    "pages_evaluated": 0,
    "findings": 0,
    "identity_clear": 0,
    "identity_gaps": 0,
    "inconsistencies": 0
  },
  "findings": [
    {
      "finding_id": "entity-...",
      "category": "entity_identity",
      "status": "present|absent|uncertain",
      "signal": "...",
      "scope": "site|page",
      "page_url": "...",
      "confidence": "high|medium|low",
      "evidence": [],
      "limitations": []
    }
  ],
  "limitations": []
}