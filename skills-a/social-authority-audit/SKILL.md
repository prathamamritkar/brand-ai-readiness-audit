---
name: social-authority-audit
description: Evaluates social proof and authority signals that influence whether AI systems consider a brand authoritative enough to cite.
license: Apache-2.0
---

# Social Authority Audit

This skill evaluates social proof and authority signals that influence whether AI systems consider a brand authoritative enough to cite. AI models rely heavily on social proof, contact information, and verifiable signals of legitimacy to determine source trustworthiness.

## Heuristics Evaluated

- **SA-001: No Review/Rating Schema**: Checks for `AggregateRating`, `Review`, or `Rating` schema types.
- **SA-002: No Social Media Profile Links**: Scans for links to major social platforms.
- **SA-003: No Contact Information Visible**: Checks for email, phone, address, or structured contact info.
- **SA-004: No Testimonial or Case Study Signals**: Scans for elements indicating testimonials or case studies.
- **SA-005: No About Page Linked**: Scans navigation/footer for "about" type pages.
- **SA-006: Missing ContactPoint or LocalBusiness Schema**: Checks for structured contact or business data.
- **SA-007: [Proactive] No Press/Media or Awards Section**: Scans for press, media coverage, or awards sections.
