#!/usr/bin/env python3

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = "freshness-corroboration/v1"

STATUS_PRESENT = "present"
STATUS_ABSENT = "absent"
STATUS_UNABLE = "unable_to_determine"

REL_CORROBORATED = "corroborated"
REL_CONFLICTING = "conflicting"
REL_SINGLE_SOURCE = "single_source"
REL_NOT_APPLICABLE = "not_applicable"
REL_UNABLE = "unable_to_determine"


VISIBLE_DATE_PATTERNS = [
    (
        "updated",
        re.compile(
            r"\b(?:last\s+)?updated\s*[:\-]?\s*"
            r"((?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},?\s+\d{4})",
            re.IGNORECASE,
        ),
    ),
    (
        "updated",
        re.compile(
            r"\b(?:last\s+)?updated\s*[:\-]?\s*"
            r"(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE,
        ),
    ),
    (
        "published",
        re.compile(
            r"\b(?:published|publication\s+date)\s*[:\-]?\s*"
            r"((?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},?\s+\d{4})",
            re.IGNORECASE,
        ),
    ),
    (
        "published",
        re.compile(
            r"\b(?:published|publication\s+date)\s*[:\-]?\s*"
            r"(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE,
        ),
    ),
]


def load_bundle(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_date(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    # ISO date / datetime.
    iso_candidate = value.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(iso_candidate)
        return parsed.date().isoformat()
    except ValueError:
        pass

    formats = [
        "%B %d, %Y",
        "%B %d %Y",
        "%d %B %Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue

    return None


def extract_jsonld_blocks(page):
    blocks = page.get("jsonld") or []

    if not isinstance(blocks, list):
        return []

    return [
        block
        for block in blocks
        if isinstance(block, dict)
    ]


def iter_jsonld_objects(block):
    yield block

    graph = block.get("@graph")

    if isinstance(graph, list):
        for item in graph:
            if isinstance(item, dict):
                yield item


def extract_structured_dates(page):
    results = []

    for block_index, block in enumerate(extract_jsonld_blocks(page)):
        for object_index, obj in enumerate(iter_jsonld_objects(block)):
            structured_type = obj.get("@type")

            if isinstance(structured_type, list):
                structured_type = ", ".join(
                    str(item) for item in structured_type
                    if item
                )

            for property_name, signal_type in (
                ("datePublished", "published"),
                ("dateModified", "updated"),
            ):
                value = obj.get(property_name)

                if not isinstance(value, str) or not value.strip():
                    continue

                normalized = normalize_date(value)

                results.append(
                    {
                        "page_url": page.get("url", ""),
                        "signal_type": signal_type,
                        "property": property_name,
                        "observed_value": value,
                        "normalized_date": normalized,
                        "jsonld_block_index": block_index,
                        "jsonld_object_index": object_index,
                        "structured_type": structured_type,
                        "evidence_field": "jsonld",
                    }
                )

    return results


def extract_visible_dates(page):
    text_parts = []

    visible_text = page.get("visible_text")

    if isinstance(visible_text, str):
        text_parts.append(visible_text)

    headings = page.get("headings") or []

    if isinstance(headings, list):
        text_parts.extend(
            item
            for item in headings
            if isinstance(item, str)
        )

    text = "\n".join(text_parts)

    if not text.strip():
        return []

    results = []

    for signal_type, pattern in VISIBLE_DATE_PATTERNS:
        for match in pattern.finditer(text):
            observed_value = match.group(1)
            normalized = normalize_date(observed_value)

            results.append(
                {
                    "page_url": page.get("url", ""),
                    "page_type": page.get("page_type") or "other",
                    "signal_type": signal_type,
                    "matched_text": match.group(0),
                    "observed_value": observed_value,
                    "normalized_date": normalized,
                    "evidence_field": "visible_text",
                }
            )

    # Deduplicate deterministically.
    unique = {}

    for item in results:
        key = (
            item["signal_type"],
            item["observed_value"],
            item["normalized_date"],
        )
        unique[key] = item

    return list(unique.values())


def build_publication_signal(page, structured_dates, visible_dates):
    structured = [
        item
        for item in structured_dates
        if item["signal_type"] == "published"
    ]

    visible = [
        item
        for item in visible_dates
        if item["signal_type"] == "published"
    ]

    if structured or visible:
        return {
            "page_url": page.get("url", ""),
            "page_type": page.get("page_type") or "other",
            "status": STATUS_PRESENT,
            "structured_count": len(structured),
            "visible_count": len(visible),
            "sources": [
                item["evidence_field"]
                for item in structured + visible
            ],
        }

    return {
        "page_url": page.get("url", ""),
        "page_type": page.get("page_type") or "other",
        "status": STATUS_ABSENT,
        "structured_count": 0,
        "visible_count": 0,
        "sources": [],
    }


def build_modification_signal(page, structured_dates, visible_dates):
    structured = [
        item
        for item in structured_dates
        if item["signal_type"] == "updated"
    ]

    visible = [
        item
        for item in visible_dates
        if item["signal_type"] == "updated"
    ]

    if structured or visible:
        return {
            "page_url": page.get("url", ""),
            "page_type": page.get("page_type") or "other",
            "status": STATUS_PRESENT,
            "structured_count": len(structured),
            "visible_count": len(visible),
            "sources": [
                item["evidence_field"]
                for item in structured + visible
            ],
        }

    return {
        "page_url": page.get("url", ""),
        "page_type": page.get("page_type") or "other",
        "status": STATUS_ABSENT,
        "structured_count": 0,
        "visible_count": 0,
        "sources": [],
    }


def determine_corroboration(visible_dates, structured_dates):
    visible_by_type = {}

    for item in visible_dates:
        if item["normalized_date"]:
            visible_by_type.setdefault(
                item["signal_type"],
                []
            ).append(item)

    structured_by_type = {}

    for item in structured_dates:
        if item["normalized_date"]:
            structured_by_type.setdefault(
                item["signal_type"],
                []
            ).append(item)

    results = []

    for signal_type in ("published", "updated"):
        visible = visible_by_type.get(signal_type, [])
        structured = structured_by_type.get(signal_type, [])

        if visible and structured:
            visible_dates_set = {
                item["normalized_date"]
                for item in visible
            }

            structured_dates_set = {
                item["normalized_date"]
                for item in structured
            }

            if visible_dates_set & structured_dates_set:
                relationship = REL_CORROBORATED
            else:
                relationship = REL_CONFLICTING

            results.append(
                {
                    "signal_type": signal_type,
                    "sources_compared": [
                        "visible_text",
                        "jsonld",
                    ],
                    "visible_values": sorted(
                        visible_dates_set
                    ),
                    "structured_values": sorted(
                        structured_dates_set
                    ),
                    "relationship": relationship,
                    "evidence_fields": [
                        "visible_text",
                        "jsonld",
                    ],
                }
            )

        elif visible or structured:
            source = (
                "visible_text"
                if visible
                else "jsonld"
            )

            values = sorted(
                {
                    item["normalized_date"]
                    for item in visible + structured
                    if item["normalized_date"]
                }
            )

            results.append(
                {
                    "signal_type": signal_type,
                    "sources_compared": [source],
                    "visible_values": (
                        values if visible else []
                    ),
                    "structured_values": (
                        values if structured else []
                    ),
                    "relationship": REL_SINGLE_SOURCE,
                    "evidence_fields": [
                        item["evidence_field"]
                        for item in visible + structured
                    ],
                }
            )

        else:
            results.append(
                {
                    "signal_type": signal_type,
                    "sources_compared": [],
                    "visible_values": [],
                    "structured_values": [],
                    "relationship": REL_NOT_APPLICABLE,
                    "evidence_fields": [],
                }
            )

    return results


def analyze_page(page):
    structured_dates = extract_structured_dates(page)
    visible_dates = extract_visible_dates(page)

    return (
        structured_dates,
        visible_dates,
        build_publication_signal(
            page,
            structured_dates,
            visible_dates,
        ),
        build_modification_signal(
            page,
            structured_dates,
            visible_dates,
        ),
        determine_corroboration(
            visible_dates,
            structured_dates,
        ),
    )


def build_coverage(pages, publication, modification):
    by_type = {}

    for page in pages:
        page_type = page.get("page_type") or "other"
        by_type.setdefault(
            page_type,
            {
                "pages": 0,
                "publication_signals": 0,
                "modification_signals": 0,
            },
        )
        by_type[page_type]["pages"] += 1

    for item in publication:
        if item["status"] == STATUS_PRESENT:
            page_type = item["page_type"]
            by_type[page_type]["publication_signals"] += 1

    for item in modification:
        if item["status"] == STATUS_PRESENT:
            page_type = item["page_type"]
            by_type[page_type]["modification_signals"] += 1

    return {
        page_type: by_type[page_type]
        for page_type in sorted(by_type)
    }


def build_summary(
    pages,
    publication,
    modification,
    visible_dates,
    structured_dates,
    corroboration,
):
    relationships = [
        item["relationship"]
        for page_items in corroboration
        for item in page_items
    ]

    return {
        "pages_analyzed": len(pages),
        "pages_with_publication_signals": sum(
            item["status"] == STATUS_PRESENT
            for item in publication
        ),
        "pages_with_modification_signals": sum(
            item["status"] == STATUS_PRESENT
            for item in modification
        ),
        "pages_with_visible_date_signals": len(
            {
                item["page_url"]
                for item in visible_dates
            }
        ),
        "pages_with_structured_date_signals": len(
            {
                item["page_url"]
                for item in structured_dates
            }
        ),
        "corroborated_signals": relationships.count(
            REL_CORROBORATED
        ),
        "conflicting_signals": relationships.count(
            REL_CONFLICTING
        ),
        "single_source_signals": relationships.count(
            REL_SINGLE_SOURCE
        ),
    }


def build_limitations(bundle, pages):
    limitations = [
        {
            "type": "evidence_scope",
            "status": STATUS_UNABLE,
            "message": (
                "Freshness analysis is limited to dates observable "
                "in the Site Intelligence evidence bundle."
            ),
        },
        {
            "type": "javascript_execution",
            "status": STATUS_UNABLE,
            "message": (
                "JavaScript-generated dates were not executed or evaluated."
            ),
        },
        {
            "type": "visual_content",
            "status": STATUS_UNABLE,
            "message": (
                "Dates rendered only through visual components or images "
                "were not evaluated."
            ),
        },
        {
            "type": "factual_currency",
            "status": STATUS_UNABLE,
            "message": (
                "The factual currency of website content was not independently "
                "verified."
            ),
        },
    ]

    crawl = bundle.get("crawl") or {}

    if crawl.get("blocked_by_robots_failure"):
        limitations.append(
            {
                "type": "robots_failure",
                "status": STATUS_UNABLE,
                "message": (
                    "The source crawl was blocked because robots.txt "
                    "could not be safely evaluated."
                ),
            }
        )

    if not pages:
        limitations.append(
            {
                "type": "no_pages",
                "status": STATUS_UNABLE,
                "message": (
                    "No pages were available for freshness analysis."
                ),
            }
        )

    return limitations


def analyze(bundle):
    pages = bundle.get("pages") or []

    if not isinstance(pages, list):
        pages = []

    publication = []
    modification = []
    visible_dates = []
    structured_dates = []
    corroboration = []

    for page in pages:
        if not isinstance(page, dict):
            continue

        (
            page_structured,
            page_visible,
            page_publication,
            page_modification,
            page_corroboration,
        ) = analyze_page(page)

        structured_dates.extend(page_structured)
        visible_dates.extend(page_visible)
        publication.append(page_publication)
        modification.append(page_modification)
        corroboration.append(
            [
                {
                    "page_url": page.get("url", ""),
                    **item,
                }
                for item in page_corroboration
            ]
        )

    return {
        "skill": "freshness-corroboration",
        "schema_version": SCHEMA_VERSION,
        "summary": build_summary(
            pages,
            publication,
            modification,
            visible_dates,
            structured_dates,
            corroboration,
        ),
        "publication_signals": publication,
        "modification_signals": modification,
        "visible_date_signals": visible_dates,
        "structured_date_signals": structured_dates,
        "corroboration": corroboration,
        "coverage": build_coverage(
            pages,
            publication,
            modification,
        ),
        "limitations": build_limitations(
            bundle,
            pages,
        ),
    }


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python analyze_freshness.py <evidence.json>",
            file=sys.stderr,
        )
        return 2

    input_path = Path(sys.argv[1])

    try:
        bundle = load_bundle(input_path)
        result = analyze(bundle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())