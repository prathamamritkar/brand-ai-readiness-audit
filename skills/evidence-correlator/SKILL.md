---
name: evidence-correlator
description: Correlates evidence from specialized audit skills to identify supported cross-signal findings, distinguish isolated observations from corroborated issues, assess evidence sufficiency and confidence, and produce traceable finding candidates. Use after specialized audit skills have analyzed the same site.
---

# Evidence Correlator

## Purpose

The Evidence Correlator combines outputs from specialized audit skills into
evidence-backed finding candidates.

It does not independently crawl websites, inspect DOM content, execute
JavaScript, determine business impact, or modify the audited website.

Its role is to answer:

> "Do multiple observed signals support the same underlying issue?"

The skill should reduce duplicate findings, strengthen findings when independent
signals corroborate each other, and preserve uncertainty when evidence is
insufficient.

---

## Inputs

The skill accepts:

- outputs from one or more specialized audit skills
- optional Site Intelligence evidence for traceability
- optional site metadata

Expected specialized evidence may include:

- machine-readability observations
- engagement observations
- crawl/render observations
- freshness observations
- future audit skill outputs

The correlator must tolerate missing skill outputs.

It must not assume that every site has evidence from every skill.

---

## Core Principles

### 1. Observation is not a finding

A single observation should not automatically become a finding.

Example:

- Observation: a page has no visible CTA.

This alone does not establish that the page has a significant engagement problem.

The correlator should preserve the observation and determine whether related
signals provide sufficient support.

### 2. Corroboration increases confidence

Independent signals pointing toward the same issue can increase confidence.

Example:

- weak machine-readable content
- weak semantic structure
- limited contextual pathways

Together these may support a stronger finding than any one signal alone.

### 3. Contradictory evidence must remain visible

If evidence sources disagree, do not silently choose one.

Represent the relationship as conflicting and reduce confidence accordingly.

### 4. Missing evidence is not negative evidence

If a specialized skill did not run or could not determine a condition, do not
interpret the missing result as an absence.

### 5. Traceability is mandatory

Every correlated finding must retain references to the evidence supporting it.

A reviewer should be able to determine:

- which skill produced the evidence
- which page or site observation was involved
- what the original observation was
- why the evidence was correlated

---

## Correlation Model

The correlator groups compatible observations into finding candidates.

A candidate should contain:

- stable candidate ID
- issue category
- concise issue statement
- supporting evidence
- contributing skills
- affected pages
- evidence relationship
- evidence sufficiency
- confidence
- limitations

The correlator should prefer a small number of well-supported candidates over
many weak or duplicate candidates.

---

## Evidence Relationships

Use these relationship labels:

### corroborated

Use when independent evidence sources support materially compatible signals
about the same issue.

### single_source

Use when the candidate is supported by one specialized skill only.

### conflicting

Use when evidence sources provide materially inconsistent signals.

### insufficient

Use when related observations exist but there is not enough evidence to
support a meaningful candidate.

### unable_to_determine

Use when the available evidence cannot establish the relationship.

---

## Evidence Sufficiency

Evaluate candidates using observable evidence only.

Use:

- `sufficient`
- `insufficient`
- `unable_to_determine`

Evidence is generally sufficient when:

- at least one concrete observation exists, and
- the observation is directly traceable to a page or site-level evidence item.

Corroboration should strengthen confidence but must not be required for every
finding.

---

## Confidence

Confidence describes how strongly the available evidence supports the
candidate.

Use:

- `high`
- `medium`
- `low`

Confidence is independent from severity or business impact.

The correlator must not assign severity based solely on the number of supporting
signals.

Suggested deterministic interpretation:

### high

Multiple independent evidence sources corroborate the same issue and the
underlying observations are concrete and traceable.

### medium

The issue has concrete traceable evidence but limited corroboration.

### low

Evidence is weak, ambiguous, conflicting, or incomplete.

---

## Deduplication

The correlator should merge observations when they describe the same underlying
issue rather than producing separate findings for each signal.

Deduplication should consider:

- normalized issue category
- affected page or page group
- semantic similarity of the issue
- contributing skill types

Do not merge observations merely because they occur on the same page.

Different issues on the same page must remain separate.

---

## Scope

The correlator may group evidence at:

- site level
- page level
- page-type level

It should preserve the smallest useful scope.

For example:

- If only `/pricing` is affected, retain page-level scope.
- If all observed product pages show the same issue, page-type grouping may be
  appropriate.
- Use site-level scope only when the evidence genuinely supports it.

---

## Output

Return an object conforming to:

`evidence-correlator/v1`

Schema:

```json
{
  "schema_version": "evidence-correlator/v1",
  "summary": {
    "candidates_considered": 0,
    "correlated_findings": 0,
    "corroborated": 0,
    "single_source": 0,
    "conflicting": 0,
    "insufficient": 0,
    "unable_to_determine": 0
  },
  "findings": [
    {
      "candidate_id": "string",
      "category": "string",
      "issue": "string",
      "scope": "site|page|page_type",
      "affected_pages": [],
      "contributing_skills": [],
      "evidence_relationship": "corroborated|single_source|conflicting|insufficient|unable_to_determine",
      "evidence_sufficiency": "sufficient|insufficient|unable_to_determine",
      "confidence": "high|medium|low",
      "evidence": [
        {
          "skill": "string",
          "page_url": "string|null",
          "signal": "string",
          "status": "present|absent|unable_to_determine",
          "source": "string"
        }
      ],
      "limitations": []
    }
  ],
  "limitations": []
}