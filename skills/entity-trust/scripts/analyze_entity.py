"""
Deterministic Entity Trust analyzer.

Evaluates observable identity signals from Site Intelligence evidence.
It does not crawl, fetch external URLs, or make reputation claims.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "entity-trust/v1"


ORGANIZATION_TERMS = {
    "about",
    "company",
    "contact",
    "organization",
    "organisation",
    "who we are",
    "our company",
    "our story",
}

OFFERING_TERMS = {
    "product",
    "products",
    "service",
    "services",
    "solution",
    "solutions",
    "pricing",
    "plans",
}


def normalize(value: Any) -> str:
    """Normalize text for deterministic comparison."""
    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def normalize_name(value: Any) -> str:
    """Normalize a potential entity name."""
    text = normalize(value)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = " ".join(text.split())

    return text


def page_url(page: dict[str, Any]) -> str:
    """Return the page URL."""
    return str(page.get("url") or page.get("page_url") or "").strip()


def page_text(page: dict[str, Any]) -> str:
    """Combine useful human-readable page evidence."""
    parts: list[str] = []

    title = page.get("title")
    description = page.get("meta_description")
    visible_text = page.get("visible_text")

    if title:
        parts.append(str(title))

    if description:
        parts.append(str(description))

    if visible_text:
        parts.append(str(visible_text))

    headings = page.get("headings", [])

    if isinstance(headings, list):
        for heading in headings:
            if isinstance(heading, dict):
                value = (
                    heading.get("text")
                    or heading.get("value")
                    or heading.get("content")
                )
            else:
                value = heading

            if value:
                parts.append(str(value))

    return normalize(" ".join(parts))


def page_type(page: dict[str, Any]) -> str:
    """Return normalized page type."""
    return normalize(page.get("page_type"))


def hostname(url: str) -> str:
    """Return normalized hostname."""
    try:
        return normalize(urlparse(url).hostname)
    except ValueError:
        return ""


def is_homepage(page: dict[str, Any]) -> bool:
    """Determine whether a page is likely the homepage."""
    kind = page_type(page)

    if kind == "homepage":
        return True

    url = page_url(page)

    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    return parsed.path in {"", "/"}


def is_about_or_contact(page: dict[str, Any]) -> bool:
    """Determine whether a page provides organization context."""
    kind = page_type(page)

    if kind in {"about", "contact"}:
        return True

    text = page_text(page)

    return any(term in text for term in ORGANIZATION_TERMS)


def is_offering_page(page: dict[str, Any]) -> bool:
    """Determine whether a page appears to describe an offering."""
    kind = page_type(page)

    if kind in {
        "product",
        "service",
        "pricing",
        "category",
    }:
        return True

    text = page_text(page)

    return any(
        re.search(rf"\b{re.escape(term)}\b", text)
        for term in OFFERING_TERMS
    )


def extract_jsonld(page: dict[str, Any]) -> list[dict[str, Any]]:
    """Return JSON-LD blocks that are JSON objects."""
    blocks = page.get("jsonld", [])

    if not isinstance(blocks, list):
        return []

    return [
        block
        for block in blocks
        if isinstance(block, dict)
    ]


def jsonld_types(page: dict[str, Any]) -> set[str]:
    """Extract JSON-LD @type values."""
    types: set[str] = set()

    for block in extract_jsonld(page):
        value = block.get("@type")

        if isinstance(value, list):
            for item in value:
                if item:
                    types.add(normalize(item))

        elif value:
            types.add(normalize(value))

    return types


def has_organization_jsonld(page: dict[str, Any]) -> bool:
    """Check for organization-like structured data."""
    types = jsonld_types(page)

    return bool(
        types
        & {
            "organization",
            "corporation",
            "localbusiness",
            "brand",
            "website",
        }
    )


def has_offering_jsonld(page: dict[str, Any]) -> bool:
    """Check for product/service-like structured data."""
    types = jsonld_types(page)

    return bool(
        types
        & {
            "product",
            "service",
            "offer",
            "softwareapplication",
        }
    )


def extract_jsonld_names(page: dict[str, Any]) -> list[str]:
    """Extract useful name values from JSON-LD."""
    names: list[str] = []

    for block in extract_jsonld(page):
        for key in ("name", "brand", "manufacturer", "provider"):
            value = block.get(key)

            if isinstance(value, dict):
                value = value.get("name")

            if isinstance(value, str) and value.strip():
                names.append(normalize_name(value))

    return sorted(set(names))


def visible_identity_candidates(page: dict[str, Any]) -> list[str]:
    """
    Extract conservative identity candidates from title and headings.

    This intentionally avoids trying to infer a complete brand name
    from arbitrary prose.
    """
    candidates: list[str] = []

    title = normalize_name(page.get("title"))

    if title:
        candidates.append(title)

    headings = page.get("headings", [])

    if isinstance(headings, list):
        for heading in headings:
            if isinstance(heading, dict):
                value = (
                    heading.get("text")
                    or heading.get("value")
                    or heading.get("content")
                )
            else:
                value = heading

            normalized = normalize_name(value)

            if normalized:
                candidates.append(normalized)

    return sorted(set(candidates))


def has_clear_organization_identity(pages: list[dict[str, Any]]) -> bool:
    """
    Determine whether site-level evidence provides organization identity.
    """
    for page in pages:
        text = page_text(page)

        if is_about_or_contact(page):
            if len(text) >= 20:
                return True

        if is_homepage(page):
            if page.get("title") or page.get("meta_description"):
                return True

        if has_organization_jsonld(page):
            return True

    return False


def offering_identity_clear(page: dict[str, Any]) -> bool:
    """Determine whether an offering page clearly describes its offering."""
    title = normalize(page.get("title"))
    description = normalize(page.get("meta_description"))
    text = page_text(page)

    has_name = bool(title)

    has_description = bool(
        description
        or len(text) >= 80
    )

    return has_name and has_description


def identity_consistency(
    pages: list[dict[str, Any]],
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Detect materially different identity names when strong evidence exists.

    The detector is intentionally conservative to avoid false positives
    from ordinary page-specific titles.
    """
    names: Counter[str] = Counter()

    evidence: list[dict[str, Any]] = []

    for page in pages:
        url = page_url(page)

        if not url:
            continue

        candidates = extract_jsonld_names(page)

        if not candidates and is_homepage(page):
            candidates = visible_identity_candidates(page)[:1]

        for name in candidates:
            if name:
                names[name] += 1

                evidence.append(
                    {
                        "page_url": url,
                        "identity": name,
                    }
                )

    if len(names) < 2:
        return False, evidence

    # Only treat names as inconsistent when multiple strong identity
    # candidates are present across relevant pages.
    common = names.most_common()

    if common[0][1] >= 2:
        conflicting = [
            item
            for item in common[1:]
            if item[1] >= 1
        ]

        if conflicting:
            return True, evidence

    return False, evidence


_SIGNAL_TITLE = {
    "organization_identity_unclear": "Organization Identity Unclear Across Site",
    "machine_identity_gap": "Machine-Readable Identity Gap",
    "offering_identity_unclear": "Offering Identity Unclear on Page",
    "identity_inconsistency": "Inconsistent Brand Identity Across Pages",
    "unstable_entity_reference": "Unstable Entity @id Across Pages",
    "entity_relationship_gap": "Entity Relationship Not Machine-Readable",
    "missing_disambiguating_description": "Organization Lacks disambiguatingDescription",
}

_SIGNAL_SEVERITY = {
    "organization_identity_unclear": "high",
    "machine_identity_gap": "high",
    "offering_identity_unclear": "medium",
    "identity_inconsistency": "medium",
    "unstable_entity_reference": "high",
    "entity_relationship_gap": "medium",
    "missing_disambiguating_description": "medium",
}

_SIGNAL_ACTION = {
    "organization_identity_unclear": "Add Organization JSON-LD with name, url, logo, sameAs, and disambiguatingDescription to the homepage and about page.",
    "machine_identity_gap": "Visible brand identity exists but no machine-readable equivalent. Add Organization JSON-LD to expose identity to AI extractors.",
    "offering_identity_unclear": "Add Product or Service JSON-LD with name, description, and category to each offering page.",
    "identity_inconsistency": "Normalize brand and product names across all pages and structured data blocks to eliminate entity conflation risk.",
    "unstable_entity_reference": "Use a single stable @id URL (e.g. https://example.com/#organization) across all Organization JSON-LD blocks.",
    "entity_relationship_gap": "Add explicit brand, manufacturer, or provider relationships in JSON-LD to link offerings to the parent Organization.",
    "missing_disambiguating_description": "Add disambiguatingDescription to Organization/Brand JSON-LD to distinguish the brand from similarly-named entities.",
}

_FINDING_COUNTER: dict[str, int] = {}


def build_finding(
    signal: str,
    status: str,
    scope: str,
    confidence: str,
    evidence: list[dict[str, Any]],
    page_url_value: str = "",
) -> dict[str, Any]:
    if signal == "entity_identity_clear":
        return {}

    prefix = "ET"
    _FINDING_COUNTER[prefix] = _FINDING_COUNTER.get(prefix, 0) + 1
    finding_id = f"{prefix}-{_FINDING_COUNTER[prefix]:03d}"

    severity = _SIGNAL_SEVERITY.get(signal, "medium")
    if signal == "unstable_entity_reference" and confidence == "medium":
        severity = "medium"

    evidence_str = "; ".join(
        str(e.get("page_url", "") or e) for e in evidence[:4]
    ) if evidence else "No supporting evidence collected."

    return {
        "id": finding_id,
        "title": _SIGNAL_TITLE.get(signal, signal.replace("_", " ").title()),
        "severity": severity,
        "gap_type": "citation",
        "category": "entity_identity",
        "url": page_url_value or "",
        "evidence": evidence_str,
        "suggested_action": {
            "summary": _SIGNAL_ACTION.get(signal, "Review entity identity signals for this issue."),
            "priority": severity,
            "scope": scope,
        },
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    """Analyze Site Intelligence evidence."""
    pages = data.get("pages", [])

    if not isinstance(pages, list):
        pages = []

    pages = [
        page
        for page in pages
        if isinstance(page, dict)
    ]

    pages = sorted(
        pages,
        key=lambda page: page_url(page),
    )

    findings: list[dict[str, Any]] = []

    # ---------------------------------------------------------------
    # Site-level organization identity
    # ---------------------------------------------------------------

    organization_evidence: list[dict[str, Any]] = []

    for page in pages:
        url = page_url(page)

        if not url:
            continue

        if is_homepage(page) or is_about_or_contact(page):
            organization_evidence.append(
                {
                    "page_url": url,
                    "page_type": page_type(page),
                    "title": str(page.get("title") or ""),
                    "has_organization_jsonld": (
                        has_organization_jsonld(page)
                    ),
                }
            )

    if has_clear_organization_identity(pages):
        findings.append(
            build_finding(
                signal="entity_identity_clear",
                status="present",
                scope="site",
                confidence=(
                    "high"
                    if len(organization_evidence) >= 2
                    else "medium"
                ),
                evidence=organization_evidence,
            )
        )
    elif pages:
        findings.append(
            build_finding(
                signal="organization_identity_unclear",
                status="absent",
                scope="site",
                confidence="medium",
                evidence=organization_evidence,
            )
        )

    # ---------------------------------------------------------------
    # Machine-readable identity gap
    # ---------------------------------------------------------------

    visible_identity_pages = [
        page
        for page in pages
        if (
            is_homepage(page)
            or is_about_or_contact(page)
        )
    ]

    visible_identity_exists = any(
        page.get("title")
        or page.get("meta_description")
        or page_text(page)
        for page in visible_identity_pages
    )

    machine_identity_exists = any(
        has_organization_jsonld(page)
        for page in pages
    )

    if visible_identity_exists and not machine_identity_exists:
        findings.append(
            build_finding(
                signal="machine_identity_gap",
                status="absent",
                scope="site",
                confidence="medium",
                evidence=[
                    {
                        "page_url": page_url(page),
                        "visible_identity": True,
                        "organization_jsonld": False,
                    }
                    for page in visible_identity_pages
                    if page_url(page)
                ],
            )
        )

    # ---------------------------------------------------------------
    # Product/service identity
    # ---------------------------------------------------------------

    offering_pages = [
        page
        for page in pages
        if is_offering_page(page)
    ]

    for page in offering_pages:
        url = page_url(page)

        if not url:
            continue

        if offering_identity_clear(page):
            findings.append(
                build_finding(
                    signal="entity_identity_clear",
                    status="present",
                    scope="page",
                    confidence="medium",
                    page_url_value=url,
                    evidence=[
                        {
                            "page_url": url,
                            "title": str(
                                page.get("title") or ""
                            ),
                            "has_description": bool(
                                page.get("meta_description")
                            ),
                            "offering_jsonld": (
                                has_offering_jsonld(page)
                            ),
                        }
                    ],
                )
            )
        else:
            findings.append(
                build_finding(
                    signal="offering_identity_unclear",
                    status="absent",
                    scope="page",
                    confidence="medium",
                    page_url_value=url,
                    evidence=[
                        {
                            "page_url": url,
                            "has_title": bool(
                                page.get("title")
                            ),
                            "has_description": bool(
                                page.get("meta_description")
                            ),
                            "offering_jsonld": (
                                has_offering_jsonld(page)
                            ),
                        }
                    ],
                )
            )

    # ---------------------------------------------------------------
    # Identity consistency
    # ---------------------------------------------------------------

    inconsistent, consistency_evidence = identity_consistency(
        pages
    )

    if inconsistent:
        findings.append(
            build_finding(
                signal="identity_inconsistency",
                status="present",
                scope="site",
                confidence="medium",
                evidence=consistency_evidence,
            )
        )

    # ---------------------------------------------------------------
    # disambiguatingDescription check (site-wide)
    # ---------------------------------------------------------------

    org_pages_with_jsonld = [
        page for page in pages if has_organization_jsonld(page)
    ]
    if org_pages_with_jsonld:
        has_disambig = any(
            any(
                block.get("disambiguatingDescription")
                for block in extract_jsonld(page)
                if isinstance(block.get("@type"), str)
                and normalize(block["@type"]) in {"organization", "corporation", "brand", "localbusiness"}
            )
            for page in org_pages_with_jsonld
        )
        if not has_disambig:
            findings.append(
                build_finding(
                    signal="missing_disambiguating_description",
                    status="absent",
                    scope="brand",
                    confidence="medium",
                    evidence=[
                        {"page_url": page_url(p), "has_org_jsonld": True, "disambiguatingDescription": False}
                        for p in org_pages_with_jsonld[:3]
                    ],
                )
            )

    # ---------------------------------------------------------------
    # Deterministic ordering and summary
    # ---------------------------------------------------------------

    findings = [
        f for f in findings if f
    ]

    findings = sorted(
        findings,
        key=lambda item: (
            {"high": 0, "medium": 1}.get(item.get("severity", "medium"), 1),
            item.get("url", ""),
            item.get("title", ""),
        ),
    )

    severity_counts = {"high": 0, "medium": 0}
    for f in findings:
        sev = f.get("severity", "medium")
        if sev in severity_counts:
            severity_counts[sev] += 1

    return {
        "site": "",
        "audited_at": "",
        "summary": {
            "total_findings": len(findings),
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
        },
        "findings": findings,
    }


def main() -> None:
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print(
            "Usage: python analyze_entity.py input.json [output.json]",
            file=sys.stderr,
        )
        raise SystemExit(1)

    input_path = sys.argv[1]

    with open(input_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")

    output = analyze(data)

    rendered = json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
    )

    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(
            rendered + "\n",
            encoding="utf-8",
        )
    else:
        print(rendered)


if __name__ == "__main__":
    main()