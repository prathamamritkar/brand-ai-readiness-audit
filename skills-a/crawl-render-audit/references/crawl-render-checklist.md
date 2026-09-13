# Crawl and Render Readiness Checklist

This document details the heuristics checked in the `crawl-render-audit` skill.

## Phase A — Crawl Access

### CR-001: AI Crawlers Blocked via robots.txt
- **What**: Verifies if popular AI bots (`GPTBot`, `Google-Extended`, `PerplexityBot`, `ClaudeBot`, `Amazonbot`) are blocked in `robots.txt`.
- **Why**: If blocked, AI search engines cannot index the site.
- **Good Looks Like**: Targeted `Allow` rules for specific bots if opting in, or omitting explicit disallow rules.

### CR-002: Meta Robots Noindex/Nosnippet
- **What**: Looks for `noindex`, `nofollow`, `nosnippet`, or `none` directives in meta tags.
- **Why**: AI systems respect standard search directives. If indexing or snippets are blocked, AI models won't read or reference the content.
- **Good Looks Like**: Removal of restrictive directives on content intended for AI discovery.

## Phase B — JS Rendering Gap

### CR-003: Severe JS Rendering Dependency
- **What**: Assesses if static HTML has fewer than 100 words.
- **Why**: Basic crawlers that do not execute JavaScript will see a blank or loading page, failing to extract core facts.
- **Good Looks Like**: Server-Side Rendering (SSR) ensuring meaningful content in the static HTML payload.

### CR-004: Moderate JS Content Risk
- **What**: Detects 100-300 words in static HTML but many external scripts.
- **Why**: Suggests a heavy reliance on JS for secondary content or partial hydration, risking incomplete indexing.
- **Good Looks Like**: Comprehensive content available without JS.

### CR-005: No Noscript Fallback
- **What**: Checks if `<noscript>` tags contain meaningful fallback content (>10 words).
- **Why**: Non-JS crawlers need fallback text to understand the page's purpose.
- **Good Looks Like**: `<noscript>` tag wrapping a text-only representation of the page content.

### CR-006: Framework Hydration Detection
- **What**: Detects markers of modern SSR frameworks (Next.js, Nuxt, React, etc.).
- **Why**: Confirms whether the site uses a framework that could be configured for SSR to solve JS rendering gaps.
- **Good Looks Like**: Presence of framework state markers if using a JS heavy stack.

## Phase C — Facts Locked in Non-Text

### CR-007: Facts Locked in Images
- **What**: Identifies if >50% of non-decorative images lack descriptive alt text (<5 words).
- **Why**: Visual information is completely lost to AI text extractors if alt text is missing or trivial (e.g., "chart").
- **Good Looks Like**: Meaningful alt text describing the data or fact depicted.

### CR-008: Media Embeds Without Text Alternatives
- **What**: Flags `iframe` videos, native `<video>` without tracks, or `<canvas>` elements missing `VideoObject` schema or transcripts.
- **Why**: Videos and canvas interactive elements are opaque boxes. Without semantic metadata, their content isn't read.
- **Good Looks Like**: Accompanying Schema.org `VideoObject` markup or an explicit on-page text transcript.

### CR-009: Site Returned Bot-Block / CAPTCHA Response
- **What**: Detects HTTP 403/429/503 responses or CAPTCHA-like page content (e.g., Cloudflare "Just a moment" pages).
- **Why**: If the site blocks automated HTTP clients, AI crawlers are similarly blocked. This also prevents false positive JS-render findings on CAPTCHA pages.
- **Good Looks Like**: Configure WAF rules to permit known AI crawler user agents while maintaining bot protection for malicious traffic.
