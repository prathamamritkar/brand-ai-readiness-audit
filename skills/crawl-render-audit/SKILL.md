---
name: crawl-render-audit
description: Analyze machine-accessibility and content-rendering signals from a Site Intelligence evidence bundle, including observable content, semantic structure, metadata, links, and limitations of non-browser collection. Use this skill when evaluating whether important website content and signals are exposed clearly to machine consumers.
---

# Crawl / Render Audit

## Purpose

Analyze the machine-accessibility and rendering signals observable in a Site Intelligence evidence bundle.

This skill determines what meaningful content and structural signals are exposed in the collected evidence and identifies situations where machine accessibility cannot be determined from static evidence alone.

The skill is observation-focused. It does not assign final severity, infer root causes, or generate recommendations.

## Input

Use a Site Intelligence evidence bundle containing, where available:

- page URL
- page type
- fetch status
- title
- meta description
- canonical URL
- language
- headings
- bounded visible text
- visible text character count
- text truncation status
- internal and external links
- JSON-LD blocks
- crawl depth
- discovery provenance

Do not perform an independent crawl.

## Audit Areas

### 1. Content Observability

Determine whether meaningful page content is observable in the collected evidence.

Consider:

- visible text presence
- visible text length
- headings
- title
- metadata
- page type
- fetch success

Do not assume that missing extracted text proves that the website has no content.

### 2. Semantic Structure

Inspect observable structural signals such as:

- page title
- headings
- heading hierarchy
- meta description
- canonical URL
- language
- semantic page-type signals

Report observations without assigning a quality score.

### 3. Machine-Discoverable Relationships

Inspect relationships exposed through:

- internal links
- contextual links
- canonical URLs
- JSON-LD relationships

Do not duplicate the detailed engagement analysis performed by the Engagement Audit skill.

### 4. Structured Rendering Signals

Inspect JSON-LD and related structured signals only when present in the Site Intelligence evidence.

Record:

- whether structured data is observable
- number of structured-data blocks
- whether structured data contains identifiable types
- whether structured data is available on important page types

Do not determine whether a JavaScript framework was used unless the evidence explicitly supports that conclusion.

### 5. Rendering Limitations

Clearly distinguish between:

- observable from collected evidence
- absent from collected evidence
- unable to determine without browser or JavaScript execution

Static extraction cannot prove that client-side rendering is or is not used.

## Evidence Rules

Every observation should include enough provenance to trace it back to the source page and evidence field.

Prefer exact evidence such as:

- page URL
- field name
- observed value
- page type
- structured-data count
- text character count
- heading count
- link count

Do not infer hidden DOM state, JavaScript execution, visual layout, CSS behavior, or user interaction.

Do not treat an empty field as proof of a rendering failure.

When evidence is insufficient, use `unable_to_determine`.

## Status Semantics

Use the following status values consistently:

### present

The relevant signal is explicitly observable in the evidence.

### absent

The relevant signal was checked and is not present in the available evidence.

### unable_to_determine

The available evidence is insufficient to make the determination reliably.

## Output Contract

Return a deterministic JSON object:

```json
{
  "skill": "crawl-render-audit",
  "schema_version": "crawl-render-audit/v1",
  "summary": {},
  "content_observability": [],
  "semantic_structure": [],
  "machine_relationships": [],
  "structured_rendering": [],
  "limitations": []
}