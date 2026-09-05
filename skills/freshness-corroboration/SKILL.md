---
name: freshness-corroboration
description: Analyze observable freshness and update signals from a Site Intelligence evidence bundle, including publication dates, modified dates, structured-data dates, and consistency across page evidence. Use this skill when evaluating whether important website information exposes clear and corroborated freshness signals to machine consumers.
---

# Freshness Corroboration

## Purpose

Analyze observable signals that indicate when website content was published, updated, or otherwise associated with a date.

The skill corroborates freshness signals across available page evidence rather than assuming that the presence of a date proves that content is current.

The skill is observation-focused. It does not decide whether content is factually outdated, assign final severity, determine root causes, or generate recommendations.

## Input

Use a Site Intelligence evidence bundle containing, where available:

- page URL
- page type
- title
- visible text
- headings
- JSON-LD blocks
- structured-data properties
- metadata
- fetch information
- crawl timestamps
- discovery provenance

Do not perform an independent crawl.

## Audit Areas

### 1. Publication Signals

Identify observable publication-date signals such as:

- `datePublished` in structured data
- publication dates represented in visible page content
- publication-related metadata when explicitly available

Record the exact source of each observed signal.

Do not infer a publication date from the URL, filename, or crawl timestamp.

### 2. Modification Signals

Identify observable update signals such as:

- `dateModified` in structured data
- visible last-updated dates
- modification-related metadata when explicitly available

A crawl timestamp is not itself a content modification date.

### 3. Structured Date Signals

Inspect JSON-LD and related structured evidence for:

- `datePublished`
- `dateModified`
- other explicitly date-related properties

Support JSON-LD `@graph` structures.

Do not assume every date-like property represents content freshness.

### 4. Visible Date Signals

Inspect visible text and headings for explicit date expressions associated with:

- publication
- updated/modified status
- articles
- blog posts
- news
- resources
- case studies
- other dated content

Use conservative deterministic matching.

A standalone year or arbitrary number should not automatically be treated as a freshness signal.

### 5. Corroboration

Compare independently observable freshness signals.

Examples:

- visible publication date matches `datePublished`
- visible update date matches `dateModified`
- publication and modification dates are both present
- visible and structured dates disagree
- only one source exposes a date
- no freshness signal is observable

Corroboration means comparing evidence sources. It does not mean verifying the factual truth of the date.

### 6. Page-Type Relevance

Consider page type when summarizing freshness coverage.

Potentially relevant page types include:

- blog
- article
- news
- case study
- resource
- documentation
- product
- service
- other

Do not assume that every page type requires a freshness signal.

## Evidence Rules

Every observation must identify enough provenance to trace it to the source page and evidence field.

Prefer evidence such as:

- page URL
- page type
- exact structured-data property
- exact structured-data value
- visible text containing the date
- metadata field
- evidence field name

Distinguish between:

- observed date
- inferred date
- unavailable date

Only observed dates may be used for corroboration.

Do not infer dates from:

- URL paths
- URL query parameters
- file names
- crawl timestamps
- HTTP timestamps unless explicitly represented as content metadata
- current system time

## Date Semantics

Normalize dates only when their source value is sufficiently explicit.

Supported examples include:

- `2026-08-20`
- `2026-08-20T14:30:00Z`
- `August 20, 2026`
- `20 August 2026`

When a date contains a time or timezone, preserve the original value and record the normalized date separately when possible.

Do not fabricate missing day or month values.

## Status Semantics

Use the following status values consistently.

### present

A relevant freshness signal is explicitly observable.

### absent

The relevant evidence was checked and no freshness signal was found.

### unable_to_determine

The available evidence is insufficient to determine the freshness state reliably.

## Corroboration Semantics

Use deterministic relationship labels such as:

### corroborated

Two or more independent observable signals represent the same date or compatible freshness event.

### conflicting

Two observable signals represent different dates for the same freshness event.

### single_source

Only one freshness source is observable.

### not_applicable

The page does not expose an applicable freshness signal in the evaluated context.

### unable_to_determine

The available evidence is insufficient to compare the signals reliably.

## Output Contract

Return a deterministic JSON object:

```json
{
  "skill": "freshness-corroboration",
  "schema_version": "freshness-corroboration/v1",
  "summary": {},
  "publication_signals": [],
  "modification_signals": [],
  "visible_date_signals": [],
  "structured_date_signals": [],
  "corroboration": [],
  "coverage": {},
  "limitations": []
}