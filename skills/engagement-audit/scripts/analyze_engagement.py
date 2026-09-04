import json
import re
import sys
from collections import Counter
from urllib.parse import urlparse


SCHEMA_VERSION = "engagement-audit/v1"


CTA_PATTERNS = [
    r"\bcontact\b",
    r"\bget started\b",
    r"\brequest (?:a )?demo\b",
    r"\bbook\b",
    r"\bbuy\b",
    r"\bsubscribe\b",
    r"\bsign up\b",
    r"\bsignup\b",
    r"\bdownload\b",
    r"\bget (?:the )?app\b",
    r"\bstart (?:a )?trial\b",
    r"\bfree trial\b",
    r"\bview pricing\b",
    r"\bpricing\b",
    r"\blearn more\b",
    r"\btry (?:it|now|for free)\b",
    r"\bregister\b",
    r"\bapply\b",
    r"\brequest\b",
]


CONTEXT_PATTERNS = {
    "product": [
        r"\bproduct\b",
        r"\bproducts\b",
        r"\bfeatures?\b",
        r"\bsolutions?\b",
    ],
    "service": [
        r"\bservices?\b",
        r"\bconsulting\b",
        r"\bsolutions?\b",
    ],
    "pricing": [
        r"\bpricing\b",
        r"\bplans?\b",
        r"\bpackages?\b",
    ],
    "documentation": [
        r"\bdocs?\b",
        r"\bdocumentation\b",
        r"\bdeveloper\b",
        r"\bapi\b",
        r"\bguide\b",
    ],
    "support": [
        r"\bsupport\b",
        r"\bhelp\b",
        r"\bknowledge base\b",
    ],
    "contact": [
        r"\bcontact\b",
        r"\bsales\b",
        r"\bget in touch\b",
    ],
    "case_study": [
        r"\bcase stud(?:y|ies)\b",
        r"\bcustomer stor(?:y|ies)\b",
    ],
    "resource": [
        r"\bresources?\b",
        r"\bwhitepaper\b",
        r"\breport\b",
        r"\bebook\b",
    ],
    "article": [
        r"\bblog\b",
        r"\barticle\b",
        r"\bnews\b",
    ],
}


GENERIC_ANCHORS = {
    "",
    "click here",
    "here",
    "read more",
    "learn more",
    "more",
    "view more",
    "details",
    "link",
}


def safe_text(value):
    if isinstance(value, str):
        return value.strip()

    if value is None:
        return ""

    return str(value).strip()


def normalize_url(url):
    if not isinstance(url, str) or not url:
        return None

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return url

    hostname = parsed.hostname.lower() if parsed.hostname else ""

    netloc = hostname

    if parsed.port:
        netloc = f"{hostname}:{parsed.port}"

    return parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        fragment="",
    ).geturl()


def same_origin(source_url, destination_url):
    source = urlparse(source_url or "")
    destination = urlparse(destination_url or "")

    if not source.netloc or not destination.netloc:
        return False

    return (
        source.scheme.lower(),
        source.netloc.lower(),
    ) == (
        destination.scheme.lower(),
        destination.netloc.lower(),
    )


def extract_link(link):
    """
    Support both the current simple URL representation and a richer
    future representation containing href/anchor text.
    """

    if isinstance(link, str):
        return {
            "url": normalize_url(link),
            "anchor_text": "",
        }

    if not isinstance(link, dict):
        return {
            "url": None,
            "anchor_text": "",
        }

    destination = (
        link.get("url")
        or link.get("href")
        or link.get("destination")
    )

    anchor_text = (
        link.get("anchor_text")
        or link.get("text")
        or link.get("label")
        or ""
    )

    return {
        "url": normalize_url(destination),
        "anchor_text": safe_text(anchor_text),
    }


def classify_anchor(anchor_text):
    text = safe_text(anchor_text).casefold()

    if not text:
        return {
            "action": False,
            "generic": True,
            "contexts": [],
        }

    action = any(
        re.search(pattern, text)
        for pattern in CTA_PATTERNS
    )

    contexts = []

    for context, patterns in CONTEXT_PATTERNS.items():
        if any(
            re.search(pattern, text)
            for pattern in patterns
        ):
            contexts.append(context)

    return {
        "action": action,
        "generic": text in GENERIC_ANCHORS,
        "contexts": contexts,
    }


def inspect_links(page, observed_urls):
    observations = []

    source_url = page.get("url")
    page_type = page.get("page_type")

    links = page.get("links", [])

    if not isinstance(links, list):
        return observations

    for index, raw_link in enumerate(links):

        link = extract_link(raw_link)

        destination = link["url"]
        anchor_text = link["anchor_text"]

        if not destination:
            observations.append(
                {
                    "type": "link_signal",
                    "url": source_url,
                    "link_index": index,
                    "status": "unable_to_determine",
                    "evidence": {
                        "anchor_text": anchor_text,
                    },
                }
            )
            continue

        classification = classify_anchor(anchor_text)

        internal = same_origin(
            source_url,
            destination,
        )

        destination_observed = (
            destination in observed_urls
        )

        observations.append(
            {
                "type": "link_signal",
                "url": source_url,
                "page_type": page_type,
                "destination": destination,
                "anchor_text": anchor_text,
                "link_scope": (
                    "internal"
                    if internal
                    else "external"
                ),
                "destination_observed": (
                    destination_observed
                    if internal
                    else None
                ),
                "action_signal": classification["action"],
                "generic_anchor": classification["generic"],
                "context_signals": classification["contexts"],
                "evidence": {
                    "source_url": source_url,
                    "destination": destination,
                    "anchor_text": anchor_text,
                },
            }
        )

    return observations


def inspect_page_engagement(page, link_observations):
    source_url = page.get("url")

    page_links = [
        item
        for item in link_observations
        if item.get("url") == source_url
    ]

    internal_links = [
        item
        for item in page_links
        if item.get("link_scope") == "internal"
    ]

    action_links = [
        item
        for item in page_links
        if item.get("action_signal") is True
    ]

    contextual_links = [
        item
        for item in page_links
        if item.get("context_signals")
    ]

    contact_links = [
        item
        for item in page_links
        if "contact" in item.get(
            "context_signals",
            [],
        )
    ]

    pricing_links = [
        item
        for item in page_links
        if "pricing" in item.get(
            "context_signals",
            [],
        )
    ]

    documentation_links = [
        item
        for item in page_links
        if "documentation" in item.get(
            "context_signals",
            [],
        )
    ]

    if action_links:
        next_action_status = "present"
    elif contextual_links:
        next_action_status = "contextual_pathway_only"
    elif internal_links:
        next_action_status = "internal_pathway_only"
    else:
        next_action_status = "absent_from_observed_evidence"

    return {
        "type": "page_engagement",
        "url": source_url,
        "page_type": page.get("page_type"),
        "next_action_status": next_action_status,
        "signals": {
            "internal_links": len(internal_links),
            "action_links": len(action_links),
            "contextual_links": len(
                contextual_links
            ),
            "contact_links": len(contact_links),
            "pricing_links": len(pricing_links),
            "documentation_links": len(
                documentation_links
            ),
        },
        "evidence": {
            "action_anchor_texts": [
                item.get("anchor_text", "")
                for item in action_links
            ],
            "contextual_anchor_texts": [
                item.get("anchor_text", "")
                for item in contextual_links
            ],
        },
    }


def inspect_navigation_pathways(link_observations):
    observations = []

    for link in link_observations:

        if link.get("link_scope") != "internal":
            continue

        observations.append(
            {
                "type": "navigation_pathway",
                "source_url": link.get("url"),
                "destination": link.get(
                    "destination"
                ),
                "anchor_text": link.get(
                    "anchor_text",
                    "",
                ),
                "destination_observed": link.get(
                    "destination_observed"
                ),
                "context_signals": link.get(
                    "context_signals",
                    [],
                ),
                "action_signal": link.get(
                    "action_signal",
                    False,
                ),
                "evidence": link.get(
                    "evidence",
                    {},
                ),
            }
        )

    return observations


def inspect_contextual_links(link_observations):
    observations = []

    for link in link_observations:

        contexts = link.get(
            "context_signals",
            [],
        )

        if not contexts:
            continue

        observations.append(
            {
                "type": "contextual_link",
                "source_url": link.get("url"),
                "destination": link.get(
                    "destination"
                ),
                "anchor_text": link.get(
                    "anchor_text",
                    "",
                ),
                "contexts": contexts,
                "internal": (
                    link.get("link_scope")
                    == "internal"
                ),
                "destination_observed": link.get(
                    "destination_observed"
                ),
                "evidence": link.get(
                    "evidence",
                    {},
                ),
            }
        )

    return observations


def analyze(bundle):
    pages = bundle.get("pages", [])

    if not isinstance(pages, list):
        pages = []

    valid_pages = [
        page
        for page in pages
        if isinstance(page, dict)
    ]

    observed_urls = {
        normalize_url(page.get("url"))
        for page in valid_pages
        if page.get("url")
    }

    link_observations = []

    for page in valid_pages:
        link_observations.extend(
            inspect_links(
                page,
                observed_urls,
            )
        )

    observations = []

    observations.extend(
        link_observations
    )

    navigation_observations = (
        inspect_navigation_pathways(
            link_observations
        )
    )

    contextual_observations = (
        inspect_contextual_links(
            link_observations
        )
    )

    observations.extend(
        navigation_observations
    )

    observations.extend(
        contextual_observations
    )

    page_engagement = []

    for page in valid_pages:
        engagement = inspect_page_engagement(
            page,
            link_observations,
        )

        page_engagement.append(
            engagement
        )

        observations.append(
            engagement
        )

    action_link_count = sum(
        1
        for item in link_observations
        if item.get("action_signal") is True
    )

    internal_link_count = sum(
        1
        for item in link_observations
        if item.get("link_scope")
        == "internal"
    )

    external_link_count = sum(
        1
        for item in link_observations
        if item.get("link_scope")
        == "external"
    )

    generic_link_count = sum(
        1
        for item in link_observations
        if item.get("generic_anchor") is True
    )

    observed_internal_destinations = sum(
        1
        for item in link_observations
        if (
            item.get("link_scope")
            == "internal"
            and item.get(
                "destination_observed"
            )
            is True
        )
    )

    pages_with_action = sum(
        1
        for item in page_engagement
        if item.get(
            "next_action_status"
        )
        == "present"
    )

    pages_with_any_pathway = sum(
        1
        for item in page_engagement
        if item.get(
            "next_action_status"
        )
        in {
            "present",
            "contextual_pathway_only",
            "internal_pathway_only",
        }
    )

    page_type_counts = Counter(
        page.get("page_type")
        for page in valid_pages
        if isinstance(
            page.get("page_type"),
            str,
        )
    )

    action_pages_by_type = Counter(
        item.get("page_type")
        for item in page_engagement
        if (
            item.get(
                "next_action_status"
            )
            == "present"
            and isinstance(
                item.get("page_type"),
                str,
            )
        )
    )

    coverage = {
        "pages_analyzed": len(
            valid_pages
        ),
        "pages_with_action_signal": (
            pages_with_action
        ),
        "pages_with_any_observed_pathway": (
            pages_with_any_pathway
        ),
        "action_page_coverage": (
            pages_with_action
            / len(valid_pages)
            if valid_pages
            else 0
        ),
        "pathway_page_coverage": (
            pages_with_any_pathway
            / len(valid_pages)
            if valid_pages
            else 0
        ),
        "page_type_counts": dict(
            page_type_counts
        ),
        "action_pages_by_type": dict(
            action_pages_by_type
        ),
    }

    return {
        "skill": "engagement-audit",
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "pages_analyzed": len(
                valid_pages
            ),
            "links_analyzed": len(
                link_observations
            ),
            "internal_links": (
                internal_link_count
            ),
            "external_links": (
                external_link_count
            ),
            "action_links": (
                action_link_count
            ),
            "generic_anchor_links": (
                generic_link_count
            ),
            "observed_internal_destinations": (
                observed_internal_destinations
            ),
            "navigation_pathways": len(
                navigation_observations
            ),
            "contextual_links": len(
                contextual_observations
            ),
        },
        "observations": observations,
        "coverage": coverage,
        "limitations": [
            "Analysis is limited to links and metadata available in the input bundle.",
            "A missing observed CTA does not prove that a page has no engagement mechanism.",
            "Visual, JavaScript-driven, form-based, and interactive engagement mechanisms may not be represented in the supplied evidence.",
            "Anchor-text classification uses deterministic patterns and does not infer unsupported user intent.",
            "Destination page types are not inferred when the destination was not present in the crawl.",
        ],
    }


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python analyze_engagement.py "
            "<evidence-bundle.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = sys.argv[1]

    with open(
        input_path,
        "r",
        encoding="utf-8",
    ) as file:
        bundle = json.load(file)

    result = analyze(bundle)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()