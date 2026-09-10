"""
Entity Trust Analyzer
Consumes a Site Intelligence Evidence Bundle and emits entity-identity findings.
Zero dependencies beyond Python 3.10+ standard library.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


# Authority domains for sameAs validation
AUTHORITY_DOMAINS = {
    "wikidata.org",
    "wikipedia.org",
    "schema.org",
    "google.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "instagram.com",
    "youtube.com",
    "pinterest.com",
}


def load_bundle(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_json_ld_nodes(bundle: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Walk every page record and extract every JSON-LD node.
    Returns list of (page_url, node_dict).
    """
    nodes: List[Tuple[str, Dict[str, Any]]] = []
    pages = bundle.get("pages", [])
    if not isinstance(pages, list):
        pages = []

    for page in pages:
        url = page.get("url", "")
        blocks = page.get("json_ld", [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            # Handle @graph arrays
            graph = block.get("@graph", [])
            if isinstance(graph, list):
                for node in graph:
                    if isinstance(node, dict):
                        nodes.append((url, node))
            else:
                nodes.append((url, block))
    return nodes


def is_entity_node(node: Dict[str, Any]) -> bool:
    t = str(node.get("@type", "")).lower()
    return any(k in t for k in ("organization", "brand", "corporation", "localbusiness", "person", "product"))


def get_entity_name(node: Dict[str, Any]) -> str:
    # Handle nested brand objects
    brand = node.get("brand")
    if isinstance(brand, dict):
        return str(brand.get("name", node.get("name", ""))).strip()
    return str(node.get("name", "")).strip()


def get_sameas_links(node: Dict[str, Any]) -> List[str]:
    raw = node.get("sameAs", [])
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(u) for u in raw if isinstance(u, str)]
    return []


def analyze(bundle: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, str]] = []
    limitations: List[str] = []

    pages = bundle.get("pages", [])
    if not isinstance(pages, list) or not pages:
        limitations.append("No pages in evidence bundle.")
        return {
            "skill": "entity-trust",
            "schema_version": "entity-trust/v1",
            "findings": findings,
            "limitations": limitations,
        }

    nodes = extract_json_ld_nodes(bundle)
    entity_nodes = [(url, n) for url, n in nodes if is_entity_node(n)]

    if not entity_nodes:
        limitations.append("No Organization, Brand, or entity JSON-LD found in bundle.")
        return {
            "skill": "entity-trust",
            "schema_version": "entity-trust/v1",
            "findings": findings,
            "limitations": limitations,
        }

    # --- 1. Identity drift: same entity type, different names across pages ---
    type_to_names: Dict[str, Set[str]] = {}
    for url, node in entity_nodes:
        t = str(node.get("@type", "Unknown")).lower()
        name = get_entity_name(node)
        if name:
            type_to_names.setdefault(t, set()).add(name)

    for entity_type, names in type_to_names.items():
        if len(names) > 1:
            findings.append({
                "category": "entity identity",
                "issue": f"{entity_type.title()} name inconsistent across pages",
                "status": "conflict",
                "page_url": bundle.get("site", {}).get("url", ""),
                "signal": f"Multiple names detected: {', '.join(sorted(names)[:3])}",
                "source": "entity trust audit",
            })

    # --- 2. Weak authority linkage: sameAs present but not pointing to authority domains ---
    for url, node in entity_nodes:
        sameas = get_sameas_links(node)
        if sameas:
            weak = [u for u in sameas if not any(d in u.lower() for d in AUTHORITY_DOMAINS)]
            if weak:
                findings.append({
                    "category": "entity authority",
                    "issue": "sameAs links lack authoritative destinations",
                    "status": "weak",
                    "page_url": url,
                    "signal": f"Non-authority sameAs: {weak[0]}",
                    "source": "entity trust audit",
                })
        else:
            # Only flag for Organization/Brand — Products don't always need sameAs
            t = str(node.get("@type", "")).lower()
            if "organization" in t or "brand" in t or "corporation" in t:
                findings.append({
                    "category": "entity authority",
                    "issue": "Missing sameAs knowledge graph bindings",
                    "status": "absent",
                    "page_url": url,
                    "signal": "Organization/Brand schema lacks sameAs links",
                    "source": "entity trust audit",
                })

    # --- 3. Disambiguation gap ---
    for url, node in entity_nodes:
        t = str(node.get("@type", "")).lower()
        if "organization" in t or "brand" in t or "corporation" in t:
            if not node.get("disambiguatingDescription"):
                findings.append({
                    "category": "entity disambiguation",
                    "issue": "Missing disambiguatingDescription",
                    "status": "absent",
                    "page_url": url,
                    "signal": "Brand entity lacks disambiguatingDescription",
                    "source": "entity trust audit",
                })

    # --- 4. Unstable @id: same entity type with different @id values ---
    type_to_ids: Dict[str, Set[str]] = {}
    for url, node in entity_nodes:
        t = str(node.get("@type", "Unknown")).lower()
        eid = node.get("@id", "")
        if eid:
            type_to_ids.setdefault(t, set()).add(eid)

    for entity_type, ids in type_to_ids.items():
        if len(ids) > 1:
            findings.append({
                "category": "entity reference",
                "issue": f"Unstable {entity_type} @id across pages",
                "status": "inconsistent",
                "page_url": bundle.get("site", {}).get("url", ""),
                "signal": f"Multiple @id values: {', '.join(sorted(ids)[:3])}",
                "source": "entity trust audit",
            })

    # --- 5. Entity fragmentation: multiple distinct org/brand nodes on same page ---
    page_orgs: Dict[str, List[str]] = {}
    for url, node in entity_nodes:
        t = str(node.get("@type", "")).lower()
        if "organization" in t or "brand" in t or "corporation" in t:
            page_orgs.setdefault(url, []).append(get_entity_name(node))

    for url, names in page_orgs.items():
        unique = set(n for n in names if n)
        if len(unique) > 1:
            findings.append({
                "category": "entity fragmentation",
                "issue": "Multiple distinct brand identities on one page",
                "status": "conflict",
                "page_url": url,
                "signal": f"Conflicting identities: {', '.join(sorted(unique)[:3])}",
                "source": "entity trust audit",
            })

    return {
        "skill": "entity-trust",
        "schema_version": "entity-trust/v1",
        "findings": findings,
        "limitations": limitations,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python analyze_entity_trust.py <evidence-bundle.json>", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        bundle = load_bundle(input_path)
        result = analyze(bundle)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
