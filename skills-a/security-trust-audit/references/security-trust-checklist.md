# Security & Trust Readiness Checklist

This document details the heuristics checked in the `security-trust-audit` skill.

## Phase A — Transport Security

### ST-001: HTTPS Not Enforced
- **What**: Checks if the target URL uses the `https://` scheme.
- **Why**: AI systems treat HTTP-only sites as untrustworthy. Google Search and AI Overviews strongly prefer HTTPS sources. Non-secure origins are flagged by browsers, reducing both human and AI trust.
- **Good Looks Like**: All pages served exclusively over HTTPS with valid certificates.

### ST-002: Missing HSTS Header
- **What**: Checks for a `Strict-Transport-Security` response header.
- **Why**: HSTS tells browsers (and crawlers) to always use HTTPS. Without it, downgrade attacks are possible and the site signals weaker security commitment.
- **Good Looks Like**: `Strict-Transport-Security: max-age=31536000; includeSubDomains` header present.

## Phase B — Security Headers

### ST-003: Missing Content-Security-Policy
- **What**: Checks for a `Content-Security-Policy` response header.
- **Why**: CSP prevents cross-site scripting (XSS) attacks. Its presence signals a security-mature site. AI systems may use security posture as a credibility signal.
- **Good Looks Like**: A CSP header defining allowed script and resource origins.

### ST-004: Missing X-Content-Type-Options
- **What**: Checks for the `X-Content-Type-Options: nosniff` header.
- **Why**: Prevents MIME-type sniffing attacks. Standard security hygiene expected of trustworthy sites.
- **Good Looks Like**: `X-Content-Type-Options: nosniff` header present.

### ST-005: Missing X-Frame-Options
- **What**: Checks for `X-Frame-Options` header or `frame-ancestors` in CSP.
- **Why**: Prevents clickjacking by controlling whether the page can be embedded in iframes. Absence signals weak security controls.
- **Good Looks Like**: `X-Frame-Options: DENY` or `SAMEORIGIN`, or `frame-ancestors` directive in CSP.

## Phase C — Trust Indicators

### ST-006: No Privacy/Terms Page Linked
- **What**: Scans the DOM for links to privacy policy, terms of service, or legal pages.
- **Why**: AI systems evaluate source trustworthiness. A site without visible legal and privacy pages appears less legitimate and less likely to be cited by AI as a credible source.
- **Good Looks Like**: Footer or navigation links to `/privacy`, `/terms`, `/legal`, or similar pages.

### ST-007: [Proactive] Missing Referrer-Policy
- **What**: Checks for a `Referrer-Policy` response header.
- **Why**: Controls how much referrer information is shared. Its presence indicates security awareness. Proactive recommendation for best practices.
- **Good Looks Like**: `Referrer-Policy: strict-origin-when-cross-origin` or similar restrictive policy.

