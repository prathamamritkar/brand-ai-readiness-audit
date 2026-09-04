import json
import sys
from collections import Counter
from urllib.parse import urlparse


SCHEMA_VERSION = "machine-readability/v1"

RELATIONSHIP_KEYS = [
    "@id",
    "url",
    "sameAs",
    "mainEntity",
    "mainEntityOfPage",
    "about",
    "isPartOf",
    "publisher",
]

IMPORTANT_PROPERTIES = {
    "name",
    "description",
    "url",
    "image",
    "logo",
    "sameAs",
    "identifier",
    "brand",
    "author",
    "publisher",
    "mainEntity",
    "mainEntityOfPage",
    "about",
    "isPartOf",
}


def safe_json(value):
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    return str(value)


def normalize_url(url):
    if not isinstance(url, str) or not url:
        return None

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        return url

    hostname = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port

    netloc = hostname

    if port:
        netloc = f"{hostname}:{port}"

    return parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        fragment="",
    ).geturl()


def expand_jsonld_blocks(page):
    """
    Flatten JSON-LD blocks and @graph entities into individual
    machine-readable entities while preserving their source block.
    """
    entities = []

    blocks = page.get("jsonld_blocks", [])

    if not isinstance(blocks, list):
        return entities

    for block_index, block in enumerate(blocks):

        if not isinstance(block, dict):
            entities.append(
                {
                    "block_index": block_index,
                    "entity_index": 0,
                    "entity": block,
                }
            )
            continue

        graph = block.get("@graph")

        if isinstance(graph, list):
            for entity_index, entity in enumerate(graph):
                if isinstance(entity, dict):
                    entities.append(
                        {
                            "block_index": block_index,
                            "entity_index": entity_index,
                            "entity": entity,
                        }
                    )

            remaining = {
                key: value
                for key, value in block.items()
                if key != "@graph"
            }

            if remaining:
                entities.append(
                    {
                        "block_index": block_index,
                        "entity_index": len(graph),
                        "entity": remaining,
                    }
                )
        else:
            entities.append(
                {
                    "block_index": block_index,
                    "entity_index": 0,
                    "entity": block,
                }
            )

    return entities


def extract_schema_types(entity):
    types = []

    if not isinstance(entity, dict):
        return types

    value = entity.get("@type")

    if isinstance(value, str):
        types.append(value)

    elif isinstance(value, list):
        types.extend(
            item
            for item in value
            if isinstance(item, str)
        )

    return types


def extract_important_properties(entity):
    if not isinstance(entity, dict):
        return {}

    properties = {}

    for key in IMPORTANT_PROPERTIES:
        if key in entity:
            properties[key] = safe_json(entity[key])

    return properties


def extract_relationships(entity):
    if not isinstance(entity, dict):
        return {}

    relationships = {}

    for key in RELATIONSHIP_KEYS:
        if key in entity:
            relationships[key] = safe_json(entity[key])

    return relationships


def inspect_jsonld(page):
    observations = []

    page_url = page.get("url")
    blocks = page.get("jsonld_blocks", [])

    if not isinstance(blocks, list):
        return observations

    for item in expand_jsonld_blocks(page):

        entity = item["entity"]
        block_index = item["block_index"]
        entity_index = item["entity_index"]

        if not isinstance(entity, dict):
            observations.append(
                {
                    "type": "structured_data",
                    "url": page_url,
                    "status": "unparseable",
                    "block_index": block_index,
                    "entity_index": entity_index,
                    "evidence": safe_json(entity),
                }
            )
            continue

        schema_types = extract_schema_types(entity)

        observations.append(
            {
                "type": "structured_data",
                "url": page_url,
                "status": "present",
                "block_index": block_index,
                "entity_index": entity_index,
                "schema_types": schema_types,
                "properties": extract_important_properties(entity),
                "evidence": {
                    "@type": entity.get("@type"),
                    "@id": entity.get("@id"),
                    "url": entity.get("url"),
                    "sameAs": entity.get("sameAs"),
                },
            }
        )

    return observations


def inspect_entities(page):
    observations = []

    page_url = page.get("url")

    for item in expand_jsonld_blocks(page):

        entity = item["entity"]

        if not isinstance(entity, dict):
            continue

        schema_types = extract_schema_types(entity)

        if not schema_types:
            continue

        observations.append(
            {
                "type": "entity",
                "url": page_url,
                "block_index": item["block_index"],
                "entity_index": item["entity_index"],
                "entity_types": schema_types,
                "entity_id": entity.get("@id"),
                "entity_name": entity.get("name"),
                "entity_url": entity.get("url"),
                "evidence": {
                    "@type": entity.get("@type"),
                    "@id": entity.get("@id"),
                    "name": entity.get("name"),
                    "url": entity.get("url"),
                },
            }
        )

    return observations


def inspect_page_identity(page):
    observations = []

    url = page.get("url")
    title = page.get("title")
    meta_description = page.get("meta_description")
    canonical = page.get("canonical")
    headings = page.get("headings", [])

    observations.append(
        {
            "type": "page_identity",
            "url": url,
            "signals": {
                "title_present": bool(title),
                "meta_description_present": bool(meta_description),
                "canonical_present": bool(canonical),
                "headings_count": (
                    len(headings)
                    if isinstance(headings, list)
                    else 0
                ),
                "language_present": bool(page.get("language")),
                "page_type_present": bool(page.get("page_type")),
            },
            "evidence": {
                "title": title,
                "meta_description": meta_description,
                "canonical": canonical,
                "language": page.get("language"),
                "page_type": page.get("page_type"),
                "headings": headings,
            },
        }
    )

    return observations


def inspect_relationships(page):
    observations = []

    page_url = page.get("url")

    for item in expand_jsonld_blocks(page):

        entity = item["entity"]

        if not isinstance(entity, dict):
            continue

        relationships = extract_relationships(entity)

        if relationships:
            observations.append(
                {
                    "type": "entity_relationship",
                    "url": page_url,
                    "block_index": item["block_index"],
                    "entity_index": item["entity_index"],
                    "relationships": relationships,
                    "entity_types": extract_schema_types(entity),
                }
            )

    return observations


def inspect_consistency(page):
    observations = []

    page_url = page.get("url")
    canonical = normalize_url(page.get("canonical"))

    for item in expand_jsonld_blocks(page):

        entity = item["entity"]

        if not isinstance(entity, dict):
            continue

        structured_url = normalize_url(
            entity.get("url")
        )

        if canonical and structured_url:

            observations.append(
                {
                    "type": "consistency",
                    "url": page_url,
                    "check": "canonical_vs_structured_url",
                    "status": (
                        "consistent"
                        if canonical == structured_url
                        else "different"
                    ),
                    "evidence": {
                        "canonical": canonical,
                        "structured_url": structured_url,
                        "block_index": item["block_index"],
                        "entity_index": item["entity_index"],
                    },
                }
            )

        entity_name = entity.get("name")
        visible_text = page.get("visible_text")

        if (
            isinstance(entity_name, str)
            and entity_name.strip()
            and isinstance(visible_text, str)
            and visible_text.strip()
        ):
            name_present = (
                entity_name.casefold()
                in visible_text.casefold()
            )

            observations.append(
                {
                    "type": "consistency",
                    "url": page_url,
                    "check": "structured_name_vs_visible_text",
                    "status": (
                        "supported"
                        if name_present
                        else "not_found_in_visible_text"
                    ),
                    "evidence": {
                        "structured_name": entity_name,
                        "visible_text_chars": len(visible_text),
                        "block_index": item["block_index"],
                        "entity_index": item["entity_index"],
                    },
                }
            )

    return observations


def analyze(bundle):
    pages = bundle.get("pages", [])

    if not isinstance(pages, list):
        pages = []

    observations = []

    structured_type_counts = Counter()
    entity_type_counts = Counter()
    page_type_counts = Counter()

    pages_with_jsonld = 0
    pages_with_entities = 0

    valid_pages = [
        page
        for page in pages
        if isinstance(page, dict)
    ]

    for page in valid_pages:

        page_type = page.get("page_type")

        if isinstance(page_type, str):
            page_type_counts[page_type] += 1

        jsonld_blocks = page.get(
            "jsonld_blocks",
            []
        )

        if (
            isinstance(jsonld_blocks, list)
            and jsonld_blocks
        ):
            pages_with_jsonld += 1

        page_entities = inspect_entities(page)

        if page_entities:
            pages_with_entities += 1

        for observation in inspect_jsonld(page):

            observations.append(observation)

            for schema_type in observation.get(
                "schema_types",
                [],
            ):
                structured_type_counts[
                    schema_type
                ] += 1

        observations.extend(
            page_entities
        )

        observations.extend(
            inspect_page_identity(page)
        )

        observations.extend(
            inspect_relationships(page)
        )

        observations.extend(
            inspect_consistency(page)
        )

        for entity in page_entities:
            for entity_type in entity.get(
                "entity_types",
                [],
            ):
                entity_type_counts[
                    entity_type
                ] += 1

    page_count = len(valid_pages)

    coverage = {
        "pages_analyzed": page_count,
        "pages_with_jsonld": pages_with_jsonld,
        "pages_with_entities": pages_with_entities,
        "jsonld_page_coverage": (
            pages_with_jsonld / page_count
            if page_count
            else 0
        ),
        "entity_page_coverage": (
            pages_with_entities / page_count
            if page_count
            else 0
        ),
        "schema_type_counts": dict(
            structured_type_counts
        ),
        "entity_type_counts": dict(
            entity_type_counts
        ),
        "page_type_counts": dict(
            page_type_counts
        ),
    }

    structured_data_blocks = sum(
        1
        for observation in observations
        if (
            observation.get("type")
            == "structured_data"
            and observation.get("status")
            == "present"
        )
    )

    entity_observations = sum(
        1
        for observation in observations
        if observation.get("type")
        == "entity"
    )

    relationship_observations = sum(
        1
        for observation in observations
        if observation.get("type")
        == "entity_relationship"
    )

    consistency_checks = sum(
        1
        for observation in observations
        if observation.get("type")
        == "consistency"
    )

    return {
        "skill": "machine-readability",
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "pages_analyzed": page_count,
            "structured_data_blocks": (
                structured_data_blocks
            ),
            "entity_observations": (
                entity_observations
            ),
            "entity_relationship_observations": (
                relationship_observations
            ),
            "consistency_checks": (
                consistency_checks
            ),
        },
        "observations": observations,
        "coverage": coverage,
        "limitations": [
            "Analysis is limited to evidence available in the input bundle.",
            "Absence of structured data in observed pages does not prove that a website lacks machine-readable information elsewhere.",
            "Semantic interpretation is intentionally conservative.",
            "JavaScript-rendered content is only analyzed when it is present in the supplied evidence bundle.",
            "Entity suitability is not judged solely from the absence of a particular Schema.org type.",
        ],
    }


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python analyze_machine_readability.py "
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