#!/usr/bin/env python3

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


SCHEMA_VERSION = "crawl-render-audit/v1"

STATUS_PRESENT = "present"
STATUS_ABSENT = "absent"
STATUS_UNABLE = "unable_to_determine"


def load_bundle(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def status_from_presence(value):
    return STATUS_PRESENT if value else STATUS_ABSENT


def get_page_type(page):
    return page.get("page_type") or "other"


def get_links(page):
    links = page.get("links") or []

    if not isinstance(links, list):
        return []

    return links


def count_link_types(page):
    internal = 0
    external = 0

    for link in get_links(page):
        if isinstance(link, str):
            destination = link
        elif isinstance(link, dict):
            destination = (
                link.get("url")
                or link.get("href")
                or link.get("destination")
                or ""
            )
        else:
            continue

        source_url = page.get("url", "")

        try:
            source_origin = (
                f"{urlparse(source_url).scheme}://"
                f"{urlparse(source_url).netloc}"
            )
            destination_parsed = urlparse(destination)

            if not destination_parsed.netloc:
                internal += 1
            else:
                destination_origin = (
                    f"{destination_parsed.scheme}://"
                    f"{destination_parsed.netloc}"
                )

                if destination_origin == source_origin:
                    internal += 1
                else:
                    external += 1
        except ValueError:
            continue

    return internal, external


def extract_jsonld_types(page):
    types = []

    for block in page.get("jsonld", []) or []:
        if not isinstance(block, dict):
            continue

        def collect_type(value):
            if isinstance(value, str) and value.strip():
                types.append(value.strip())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.strip():
                        types.append(item.strip())

        collect_type(block.get("@type"))

        graph = block.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    collect_type(item.get("@type"))

    # Deterministic ordering and deduplication.
    return sorted(set(types), key=str.lower)


def analyze_content_observability(page):
    url = page.get("url", "")
    page_type = get_page_type(page)

    visible_text = page.get("visible_text")
    visible_chars = page.get("visible_text_chars")

    if not isinstance(visible_chars, int):
        if isinstance(visible_text, str):
            visible_chars = len(visible_text)
        else:
            visible_chars = 0

    headings = page.get("headings") or []
    title = page.get("title")

    fetch = page.get("fetch") or {}
    fetch_ok = fetch.get("ok")

    if fetch_ok is False:
        status = STATUS_UNABLE
    elif visible_chars > 0 or len(headings) > 0 or bool(title):
        status = STATUS_PRESENT
    else:
        status = STATUS_UNABLE

    return {
        "page_url": url,
        "page_type": page_type,
        "status": status,
        "visible_text_chars": visible_chars,
        "heading_count": len(headings),
        "title_present": bool(title),
        "text_truncated": bool(page.get("visible_text_truncated")),
        "evidence_fields": [
            "fetch.ok",
            "visible_text",
            "visible_text_chars",
            "headings",
            "title",
        ],
    }


def analyze_semantic_structure(page):
    url = page.get("url", "")
    page_type = get_page_type(page)

    title = page.get("title")
    headings = page.get("headings") or []
    meta_description = page.get("meta_description")
    canonical = page.get("canonical")
    language = page.get("language")

    heading_status = (
        STATUS_PRESENT
        if len(headings) > 0
        else STATUS_ABSENT
    )

    return {
        "page_url": url,
        "page_type": page_type,
        "title": {
            "status": status_from_presence(bool(title)),
            "value": title if title else None,
        },
        "headings": {
            "status": heading_status,
            "count": len(headings),
        },
        "meta_description": {
            "status": status_from_presence(bool(meta_description)),
            "value": meta_description if meta_description else None,
        },
        "canonical": {
            "status": status_from_presence(bool(canonical)),
            "value": canonical if canonical else None,
        },
        "language": {
            "status": status_from_presence(bool(language)),
            "value": language if language else None,
        },
        "page_type": page_type,
        "evidence_fields": [
            "title",
            "headings",
            "meta_description",
            "canonical",
            "language",
            "page_type",
        ],
    }


def analyze_machine_relationships(page):
    url = page.get("url", "")
    internal_links, external_links = count_link_types(page)

    canonical = page.get("canonical")
    jsonld_types = extract_jsonld_types(page)

    if canonical:
        canonical_status = STATUS_PRESENT
    else:
        canonical_status = STATUS_ABSENT

    if jsonld_types:
        structured_status = STATUS_PRESENT
    else:
        structured_status = STATUS_ABSENT

    return {
        "page_url": url,
        "internal_link_count": internal_links,
        "external_link_count": external_links,
        "canonical": {
            "status": canonical_status,
            "value": canonical if canonical else None,
        },
        "structured_relationships": {
            "status": structured_status,
            "types": jsonld_types,
        },
        "evidence_fields": [
            "links",
            "canonical",
            "jsonld",
        ],
    }


def analyze_structured_rendering(page):
    url = page.get("url", "")
    blocks = page.get("jsonld") or []
    jsonld_types = extract_jsonld_types(page)

    if blocks:
        status = STATUS_PRESENT
    else:
        status = STATUS_ABSENT

    return {
        "page_url": url,
        "status": status,
        "jsonld_block_count": len(blocks),
        "observable_types": jsonld_types,
        "evidence_fields": [
            "jsonld",
        ],
    }


def build_summary(pages, content, semantic, relationships, structured):
    pages_with_content = sum(
        item["status"] == STATUS_PRESENT
        for item in content
    )

    pages_with_title = sum(
        item["title"]["status"] == STATUS_PRESENT
        for item in semantic
    )

    pages_with_headings = sum(
        item["headings"]["status"] == STATUS_PRESENT
        for item in semantic
    )

    pages_with_metadata = sum(
        item["meta_description"]["status"] == STATUS_PRESENT
        for item in semantic
    )

    pages_with_structured_data = sum(
        item["status"] == STATUS_PRESENT
        for item in structured
    )

    pages_with_internal_links = sum(
        item["internal_link_count"] > 0
        for item in relationships
    )

    pages_unable_to_determine_rendering = len(pages)

    page_types = Counter(get_page_type(page) for page in pages)

    return {
        "pages_analyzed": len(pages),
        "pages_with_observable_content": pages_with_content,
        "pages_with_titles": pages_with_title,
        "pages_with_headings": pages_with_headings,
        "pages_with_meta_descriptions": pages_with_metadata,
        "pages_with_structured_data": pages_with_structured_data,
        "pages_with_internal_links": pages_with_internal_links,
        "pages_rendering_unable_to_determine": (
            pages_unable_to_determine_rendering
        ),
        "page_type_distribution": dict(
            sorted(page_types.items())
        ),
    }


def build_limitations(bundle, pages):
    limitations = [
        {
            "type": "javascript_execution",
            "status": STATUS_UNABLE,
            "message": (
                "JavaScript execution was not performed; "
                "client-side rendering cannot be proven from static evidence."
            ),
        },
        {
            "type": "visual_rendering",
            "status": STATUS_UNABLE,
            "message": (
                "Visual rendering was not evaluated, including CSS visibility "
                "and layout-dependent content."
            ),
        },
        {
            "type": "interactive_elements",
            "status": STATUS_UNABLE,
            "message": (
                "Forms, interactive widgets, and user-triggered content "
                "were not executed."
            ),
        },
        {
            "type": "bounded_text",
            "status": STATUS_UNABLE,
            "message": (
                "Visible text may be bounded or truncated according to "
                "Site Intelligence collection limits."
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
                    "No pages were available for analysis in the "
                    "Site Intelligence evidence bundle."
                ),
            }
        )

    return limitations


def analyze(bundle):
    pages = bundle.get("pages") or []

    if not isinstance(pages, list):
        pages = []

    content = []
    semantic = []
    relationships = []
    structured = []

    for page in pages:
        if not isinstance(page, dict):
            continue

        content.append(
            analyze_content_observability(page)
        )

        semantic.append(
            analyze_semantic_structure(page)
        )

        relationships.append(
            analyze_machine_relationships(page)
        )

        structured.append(
            analyze_structured_rendering(page)
        )

    summary = build_summary(
        pages,
        content,
        semantic,
        relationships,
        structured,
    )

    return {
        "skill": "crawl-render-audit",
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "content_observability": content,
        "semantic_structure": semantic,
        "machine_relationships": relationships,
        "structured_rendering": structured,
        "limitations": build_limitations(bundle, pages),
    }


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python analyze_crawl_render.py <evidence.json>",
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

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())