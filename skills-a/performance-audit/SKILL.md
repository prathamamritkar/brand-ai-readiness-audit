---
name: performance-audit
description: Analyzes page performance signals that affect AI crawl budget and user bounce rates.
license: Apache-2.0
---

# Performance Audit Skill

This skill analyzes static HTML to detect performance bottlenecks that could impact AI crawler efficiency and user experience. All checks work on static HTML analysis without requiring a headless browser.

## Heuristics Evaluated

*   **PA-001: Excessive External Scripts**: Flags when there are more than 15 external scripts.
*   **PA-002: Render-Blocking Resources**: Flags when there are more than 5 render-blocking stylesheets or scripts in the `<head>`.
*   **PA-003: Excessive Page Weight (Inline)**: Flags HTML document sizes over 500KB.
*   **PA-004: No Lazy Loading on Images**: Flags when more than 5 images (excluding the first 3) lack the `loading="lazy"` attribute.
*   **PA-005: Inline CSS Bloat**: Flags when total inline CSS exceeds 50KB.
*   **PA-006: No Resource Hints**: Flags the absence of preconnect, dns-prefetch, or preload resource hints.
*   **PA-007: [Proactive] No Web App Manifest**: Flags the absence of a linked web app manifest.
