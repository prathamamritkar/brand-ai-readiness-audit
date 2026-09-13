---
name: crawl-render-audit
description: Analyzes if AI crawlers can reach and extract content from a URL. Checks for robots.txt blocks, meta tags blocking indexing, heavy client-side JavaScript dependencies, and whether core facts are locked inside non-text elements (images, iframes, videos) without fallbacks.
license: Apache-2.0
---

# Crawl & Render Audit Skill

## When to use
Use this skill when you need to answer the diagnostic question: "Can AI crawlers reach and extract the content?" This identifies baseline discoverability issues where crawlers fail to read the content entirely.

## Inputs
- URL to analyze.

## Procedure
1. **Phase A — Crawl Access:** Check `robots.txt` rules and `<meta>` tags for directives that block popular AI bots (GPTBot, ClaudeBot, etc.) or standard indexing (`noindex`, `nosnippet`).
2. **Phase B — JS Rendering Gap:** Analyze the static HTML to measure meaningful word count without JavaScript execution. Determine if the page relies heavily on client-side rendering (CSR) without fallbacks, potentially hiding content from basic crawlers.
3. **Phase C — Facts Locked in Non-Text:** Inspect images, iframes, and media tags for textual alternatives (alt text, transcripts, schema). Lack of these means embedded facts are invisible to AI.

## Output Format
Returns an array of finding objects following the standard schema format:
`id`, `title`, `severity`, `evidence`, and `suggested_action` (with `summary` and `priority`).

See `references/crawl-render-checklist.md` for detailed rules and rationale.
