# Performance Audit Reference Checklist

## PA-001: Excessive External Scripts
**What:** The page loads more than 15 external scripts (`<script src="...">` tags pointing to external domains).
**Why:** Too many external scripts require multiple DNS lookups, TCP handshakes, and TLS negotiations, increasing page load time and consuming AI crawl budget.
**Good Looks Like:** Keep external script count low by bundling, deferring, or removing unnecessary third-party scripts.

## PA-002: Render-Blocking Resources
**What:** More than 5 stylesheets or non-async/defer scripts in the `<head>`.
**Why:** Browsers pause DOM construction when they encounter synchronous scripts or stylesheets. Reducing them speeds up initial rendering.
**Good Looks Like:** Use `async` or `defer` for non-critical scripts and inline critical CSS or reduce the number of `<link rel="stylesheet">` tags.

## PA-003: Excessive Page Weight (Inline)
**What:** The total size of the HTML document itself exceeds 500KB.
**Why:** A heavy HTML document wastes network bandwidth and requires more processing time for AI crawlers.
**Good Looks Like:** Keep HTML clean and concise. Avoid excessive inline base64 images, large JSON blobs, or huge style blocks if they can be separated.

## PA-004: No Lazy Loading on Images
**What:** Missing the `loading="lazy"` attribute on off-screen images (images after the first 3).
**Why:** Eagerly loading all images wastes bandwidth on images the user might never scroll down to see. It slows down the initial page load.
**Good Looks Like:** All non-critical, below-the-fold images should have `loading="lazy"`.

## PA-005: Inline CSS Bloat
**What:** More than 50KB of inline CSS in `<style>` blocks.
**Why:** While inlining critical CSS can be good, excessive inline CSS balloons the HTML payload and prevents caching of the CSS across different pages.
**Good Looks Like:** Extract large CSS into external files so they can be cached by the browser and CDN.

## PA-006: No Resource Hints
**What:** No `preconnect`, `dns-prefetch`, or `preload` tags found.
**Why:** Resource hints allow browsers to proactively perform DNS lookups or establish connections to important third-party origins, reducing latency later in the load cycle.
**Good Looks Like:** Critical third-party origins (like font or analytics servers) have `preconnect` tags in the document head.

## PA-007: [Proactive] No Web App Manifest
**What:** The page doesn't link to a Web App Manifest.
**Why:** A manifest allows the site to act as a Progressive Web App (PWA) and signals to crawlers that the site follows modern performance and usability standards.
**Good Looks Like:** Include `<link rel="manifest" href="/manifest.json">` pointing to a valid web app manifest file.
