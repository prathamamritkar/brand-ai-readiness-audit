---
name: recommendation-engine
description: Convert evidence-backed audit findings into prioritized, actionable recommendations with root causes, expected outcomes, and verification guidance. Use after evidence correlation when findings need remediation guidance.
---

# Recommendation Engine

## Purpose

The Recommendation Engine transforms evidence-backed audit findings into clear, prioritized recommendations.

It does not perform crawling, DOM inspection, external network requests, or website modifications. It does not invent findings or assume that an issue exists without supporting evidence.

## Inputs

The skill accepts:

- Evidence Correlator output
- Finding category and issue
- Affected page or site scope
- Evidence and contributing skills
- Evidence sufficiency
- Confidence
- Existing limitations

Missing or uncertain evidence must remain visible.

## Core Principles

### 1. Evidence before recommendation

Only findings with sufficient evidence should receive a concrete recommendation.

Insufficient or undetermined findings may receive a verification recommendation rather than a remediation claim.

### 2. Root-cause oriented

Recommendations should explain:

**Problem → Root cause → Recommended action → Expected outcome → Verification**

Avoid generic advice such as "improve SEO" or "add more content."

### 3. Prioritization

Prioritize findings using:

- Severity or impact when provided
- Confidence
- Evidence sufficiency
- Scope
- User/agent engagement impact

Confidence must not be treated as severity.

### 4. Minimal assumptions

Recommendations must be provider-neutral and applicable across different website architectures and industries.

Do not assume a particular CMS, framework, hosting platform, analytics provider, or AI provider unless the evidence explicitly identifies it.

### 5. Actionability

Every concrete recommendation should identify:

- What should change
- Why it matters
- Where it applies
- How success can be verified

### 6. No false certainty

Do not convert a missing observation into a definitive business claim.

Use wording such as "review," "consider," or "verify" when evidence is incomplete.

## Recommendation Categories

Use the finding category when possible.

Common mappings include:

- `entity_identity` → strengthen organization/product identity signals
- `machine_structure` → improve structured machine-readable representation
- `semantic_structure` → improve semantic page structure
- `engagement_pathway` → clarify primary engagement pathways
- `navigation_pathway` → improve navigation and discoverability pathways
- `render_observability` → ensure important content is observable in the rendered experience
- `freshness_signal` → strengthen freshness and update signals

Unknown categories must still receive provider-neutral recommendations based only on the supplied evidence.

## Priority

Use one of:

- `critical`
- `high`
- `medium`
- `low`

If the input contains a severity value, preserve it when valid.

Otherwise derive priority conservatively:

- High confidence + sufficient evidence + broad or important scope → `high`
- Medium confidence + sufficient evidence → `medium`
- Low confidence or limited scope → `low`

Never assign `critical` solely from missing evidence.

## Output Schema

Return:

```json
{
  "schema_version": "recommendation-engine/v1",
  "summary": {
    "recommendations_generated": 0,
    "high_priority": 0,
    "medium_priority": 0,
    "low_priority": 0,
    "verification_required": 0
  },
  "recommendations": [
    {
      "recommendation_id": "recommendation-...",
      "candidate_id": "...",
      "category": "...",
      "priority": "high|medium|low|critical",
      "title": "...",
      "problem": "...",
      "root_cause": "...",
      "action": "...",
      "expected_outcome": "...",
      "verification": "...",
      "scope": "site|page",
      "affected_pages": [],
      "confidence": "high|medium|low",
      "evidence_sufficiency": "sufficient|insufficient|unable_to_determine",
      "evidence": [],
      "limitations": []
    }
  ],
  "limitations": []
}