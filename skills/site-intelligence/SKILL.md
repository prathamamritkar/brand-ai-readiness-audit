---
name: site-intelligence
description: Collect bounded, read-only evidence from a public website for downstream AI-discoverability and engagement audits. Use when an audit needs crawl, page, link, metadata, robots.txt, sitemap, or structured-data evidence.
license: MIT
compatibility: Requires Python 3.10+ and network access to the public target website.
allowed-tools: Bash(python:*)
---

# Site Intelligence

## Purpose

Build the shared evidence bundle that downstream audit skills consume. This skill collects observations; it does not decide whether an observation is a defect.

## Procedure

1. Normalize the supplied URL to an HTTP(S) origin.
2. Fetch and parse `robots.txt` when available.
3. Discover a sitemap from `robots.txt` and the conventional `/sitemap.xml` location.
4. Crawl a bounded set of same-origin HTML pages while respecting `robots.txt`.
5. Record page-level evidence:
   - URL and HTTP status
   - final URL after redirects
   - content type
   - page title
   - meta description
   - headings
   - visible text length
   - links
   - JSON-LD blocks
   - canonical URL
6. Prefer breadth across discovered pages and enforce hard page, byte, depth, and time limits.
7. Return the evidence bundle as JSON.
8. If a page cannot be fetched or parsed, record the failure as evidence rather than inventing page content.

## Output

The script `scripts/crawl_site.py` emits a versioned JSON evidence bundle.

This skill is intentionally observation-only. Severity, confidence, root-cause analysis, and recommendations belong to downstream skills.

## Safety and limits

- Read-only requests only.
- Same-origin crawling only.
- Respect `robots.txt` when it is available.
- No authentication, form submission, or state-changing requests.
- Default budget: 20 pages, depth 2, 2 MiB per response, 120 seconds total.
