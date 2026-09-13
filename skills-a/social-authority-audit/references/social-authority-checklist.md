# Social Authority Audit Checklist

## SA-001: No Review/Rating Schema
- **What**: Verifies the presence of `AggregateRating`, `Review`, or `Rating` structured data.
- **Why**: AI systems look for verified social proof to rank the legitimacy of businesses.
- **Good Looks Like**: JSON-LD scripts containing `AggregateRating` schemas linked to actual customer reviews.

## SA-002: No Social Media Profile Links
- **What**: Scans for links to recognizable social platforms (Twitter, Facebook, LinkedIn, etc.).
- **Why**: Active social media profiles corroborate brand identity and help AI models with disambiguation.
- **Good Looks Like**: Visible links to official social media properties, often structured in the footer or contact pages.

## SA-003: No Contact Information Visible
- **What**: Checks for explicit contact methods like `mailto:`, `tel:`, or HTML `<address>` elements, or structured schema.
- **Why**: Publicly visible contact information builds trust and provides clear signals of a legitimate, reachable business.
- **Good Looks Like**: Accessible phone numbers or email links, and an embedded address section.

## SA-004: No Testimonial or Case Study Signals
- **What**: Looks for classes or IDs containing words like "testimonial", "case-study", or "customer-story".
- **Why**: Content highlighting customer success acts as essential social proof for LLM knowledge graphs.
- **Good Looks Like**: Dedicated blocks or pages featuring case studies or customer testimonials with appropriate semantic markup.

## SA-005: No About Page Linked
- **What**: Checks navigation menus and footers for links pointing to "About", "Team", or "Company" pages.
- **Why**: Brand narrative pages help AI systems build contextual entity knowledge about the organization.
- **Good Looks Like**: Prominent links to an "About Us" page detailing the company's mission and team.

## SA-006: Missing ContactPoint or LocalBusiness Schema
- **What**: Ensures `Organization` schema includes `ContactPoint` or `LocalBusiness`/`PostalAddress` properties.
- **Why**: Enriched organization data feeds directly into structured AI understanding.
- **Good Looks Like**: Comprehensive JSON-LD data representing the organization's headquarters and contact info.

## SA-007: [Proactive] No Press/Media or Awards Section
- **What**: Scans for sections titled "Press", "Media", "Awards", or "Featured In".
- **Why**: Third-party validation (PR, media, awards) greatly strengthens AI citation confidence and trust metrics.
- **Good Looks Like**: A dedicated section or page aggregating media mentions, press releases, and earned awards.
