#!/usr/bin/env python3

"""
Evidence Correlator

Combines specialized audit evidence into deterministic,
traceable finding candidates.

Usage:
    python analyze_evidence.py input.json
    python analyze_evidence.py input.json output.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SKILL_NAMES = {
    "crawl-render-audit",
    "engagement-audit",
    "entity-trust",
    "freshness-corroboration",
    "machine-readability",
}

STATUS_VALUES = {
    "present",
    "absent",
    "unable_to_determine",
}


def empty_summary() -> Dict[str, int]:
    return {
        "candidates_considered": 0,
        "correlated_findings": 0,
        "corroborated": 0,
        "single_source": 0,
        "conflicting": 0,
        "insufficient": 0,
        "unable_to_determine": 0,
    }


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
        )

    return str(value).strip()


def normalize_url(value: Any) -> Optional[str]:
    text = clean_text(value)

    if not text:
        return None

    return text.strip().rstrip("/")


def normalize_key(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_page_url(item: Dict[str, Any]) -> Optional[str]:
    for key in (
        "page_url",
        "url",
        "page",
        "pageUrl",
    ):
        if key in item:
            result = normalize_url(item.get(key))

            if result:
                return result

    return None


def get_status(item: Dict[str, Any]) -> str:
    status = clean_text(
        item.get("status")
    ).lower()

    if status in STATUS_VALUES:
        return status

    return "unable_to_determine"


def extract_skill_name(
    item: Dict[str, Any],
    default: str,
) -> str:
    for key in (
        "skill",
        "source_skill",
        "contributing_skill",
    ):
        value = clean_text(item.get(key))

        if value:
            return value

    return default


def extract_signal(item: Dict[str, Any]) -> str:
    for key in (
        "signal",
        "issue",
        "finding",
        "observation",
        "reason",
        "description",
        "message",
        "criterion",
        "check",
    ):
        value = clean_text(item.get(key))

        if value:
            return value

    return ""


def extract_category(
    item: Dict[str, Any],
    skill: str,
) -> str:
    for key in (
        "category",
        "area",
        "type",
        "issue_category",
        "finding_type",
    ):
        value = clean_text(item.get(key))

        if value:
            return normalize_key(value).replace(
                " ",
                "_",
            )

    return normalize_key(skill).replace(
        " ",
        "_",
    )


def iter_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from iter_dicts(child)

    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def looks_like_observation(
    item: Dict[str, Any],
) -> bool:
    observation_keys = {
        "status",
        "signal",
        "observation",
        "issue",
        "finding",
        "description",
        "reason",
        "criterion",
    }

    return bool(
        observation_keys.intersection(
            item.keys()
        )
    )


def collect_observations(
    skill_name: str,
    payload: Any,
) -> List[Dict[str, Any]]:
    observations: List[Dict[str, Any]] = []

    source = (
        payload.get("findings")
        if isinstance(payload, dict)
        and isinstance(payload.get("findings"), list)
        else []
    )

    for item in iter_dicts(source):
        if not looks_like_observation(item):
            continue

        signal = extract_signal(item)

        if not signal:
            continue

        observations.append(
            {
                "skill": extract_skill_name(
                    item,
                    skill_name,
                ),
                "page_url": get_page_url(item),
                "category": extract_category(
                    item,
                    skill_name,
                ),
                "signal": signal,
                "status": get_status(item),
                "source": (
                    clean_text(
                        item.get("source")
                    )
                    or clean_text(
                        item.get("evidence")
                    )
                    or "specialized audit output"
                ),
            }
        )

    return observations


def extract_skill_payloads(
    input_data: Any,
) -> Dict[str, Any]:
    if not isinstance(input_data, dict):
        return {}

    if isinstance(
        input_data.get("skills"),
        dict,
    ):
        return input_data["skills"]

    result: Dict[str, Any] = {}

    for skill_name in SKILL_NAMES:
        if skill_name in input_data:
            result[skill_name] = input_data[
                skill_name
            ]

    return result


def canonical_signal(signal: str) -> str:
    text = normalize_key(signal)

    replacements = {
        "not_present": "absent",
        "missing": "absent",
        "not_available": "unable to determine",
        "unknown": "unable to determine",
    }

    return replacements.get(
        text,
        text,
    )


def issue_family(
    category: str,
    signal: str,
) -> str:
    """
    Deterministic issue-family mapping.

    Explicit keyword rules are used instead of
    semantic or LLM similarity.
    """

    text = (
        f"{category} {signal}"
    ).lower()

    rules = (
        (
            (
                "entity",
                "organization",
                "identity",
                "brand",
            ),
            "entity_identity",
        ),
        (
            (
                "schema",
                "structured data",
                "json ld",
                "jsonld",
                "machine readable",
                "machine-readable",
                "structured content",
            ),
            "machine_structure",
        ),
        (
            (
                "semantic",
                "heading",
                "content observability",
                "semantic structure",
            ),
            "semantic_structure",
        ),
        (
            (
                "cta",
                "call to action",
                "engagement",
                "next action",
            ),
            "engagement_pathway",
        ),
        (
            (
                "navigation",
                "contextual link",
                "internal link",
                "link pathway",
            ),
            "navigation_pathway",
        ),
        (
            (
                "render",
                "rendering",
                "javascript",
                "js",
                "crawl",
            ),
            "render_observability",
        ),
        (
            (
                "freshness",
                "publication",
                "published",
                "modified",
                "updated",
                "date",
            ),
            "freshness_signal",
        ),
    )

    for keywords, family in rules:
        if any(
            keyword in text
            for keyword in keywords
        ):
            return family

    return (
        normalize_key(category)
        or "general"
    )


def signal_tokens(
    observation: Dict[str, Any],
) -> set:
    text = (
        f"{observation['category']} "
        f"{observation['signal']}"
    ).lower()

    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            text,
        )
        if len(token) > 2
    }


def signals_are_compatible(
    left: Dict[str, Any],
    right: Dict[str, Any],
) -> bool:
    """
    Prevent unrelated observations from being merged
    simply because they share a broad issue family.
    """

    left_signal = canonical_signal(
        left["signal"]
    )

    right_signal = canonical_signal(
        right["signal"]
    )

    if left_signal == right_signal:
        return True

    left_tokens = signal_tokens(left)
    right_tokens = signal_tokens(right)

    overlap = left_tokens.intersection(
        right_tokens
    )

    meaningful_overlap = {
        token
        for token in overlap
        if token not in {
            "page",
            "content",
            "site",
            "observed",
            "available",
            "present",
            "absent",
            "missing",
            "issue",
        }
    }

    return len(meaningful_overlap) >= 2


def signals_share_machine_structure_issue(
    left: Dict[str, Any],
    right: Dict[str, Any],
) -> bool:
    """
    Allow explicit machine/semantic/render correlation
    only when both observations describe a shared
    structural or observability problem.
    """

    left_text = (
        f"{left['category']} "
        f"{left['signal']}"
    ).lower()

    right_text = (
        f"{right['category']} "
        f"{right['signal']}"
    ).lower()

    structural_terms = {
        "structured",
        "structure",
        "schema",
        "json",
        "jsonld",
        "semantic",
        "heading",
        "machine",
        "render",
        "rendering",
        "javascript",
        "js",
        "crawl",
        "observable",
        "observability",
    }

    left_terms = {
        term
        for term in structural_terms
        if term in left_text
    }

    right_terms = {
        term
        for term in structural_terms
        if term in right_text
    }

    return bool(
        left_terms.intersection(
            right_terms
        )
    )


def compatible(
    left: Dict[str, Any],
    right: Dict[str, Any],
) -> bool:
    """
    Determine whether two observations can belong
    to the same finding candidate.

    Correlation is intentionally conservative.
    Same-page observations are not automatically
    considered the same issue.
    """

    left_family = issue_family(
        left["category"],
        left["signal"],
    )

    right_family = issue_family(
        right["category"],
        right["signal"],
    )

    left_page = left["page_url"]
    right_page = right["page_url"]

    # Page-level observations correlate only when
    # they refer to the same page.
    if (
        left_page
        and right_page
        and left_page != right_page
    ):
        return False

    # Same family requires compatible signal meaning.
    if left_family == right_family:
        return signals_are_compatible(
            left,
            right,
        )

    family_pair = frozenset(
        {
            left_family,
            right_family,
        }
    )

    # Explicit cross-family structural relationships.
    if family_pair == frozenset(
        {
            "machine_structure",
            "semantic_structure",
        }
    ):
        return signals_share_machine_structure_issue(
            left,
            right,
        )

    if family_pair == frozenset(
        {
            "machine_structure",
            "render_observability",
        }
    ):
        return signals_share_machine_structure_issue(
            left,
            right,
        )

    if family_pair == frozenset(
        {
            "semantic_structure",
            "render_observability",
        }
    ):
        return signals_share_machine_structure_issue(
            left,
            right,
        )

    # Engagement and navigation are related domains,
    # but they must not be merged merely because they
    # occur on the same page.
    return False


def candidate_issue(
    family: str,
    observations: List[Dict[str, Any]],
) -> str:
    labels = {
        "entity_identity":
            "Entity and brand identity signals require review",

        "machine_structure":
            "Machine-readable structure requires review",

        "semantic_structure":
            "Semantic content structure requires review",

        "engagement_pathway":
            "Engagement pathways require review",

        "navigation_pathway":
            "Navigation and contextual pathways require review",

        "render_observability":
            "Rendered content observability requires review",

        "freshness_signal":
            "Content freshness signals require review",
    }

    if family in labels:
        return labels[family]

    return observations[0]["signal"]


def relationship_for(
    observations: List[Dict[str, Any]],
) -> str:
    skills = {
        observation["skill"]
        for observation in observations
        if observation["status"]
        != "unable_to_determine"
    }

    statuses = {
        observation["status"]
        for observation in observations
        if observation["status"]
        != "unable_to_determine"
    }

    if not skills:
        return "unable_to_determine"

    if len(statuses) > 1:
        return "conflicting"

    if len(skills) > 1:
        return "corroborated"

    return "single_source"


def sufficiency_for(
    observations: List[Dict[str, Any]],
) -> str:
    concrete = [
        observation
        for observation in observations
        if observation["status"]
        in {
            "present",
            "absent",
        }
    ]

    if concrete:
        return "sufficient"

    if observations:
        return "unable_to_determine"

    return "insufficient"


def confidence_for(
    relationship: str,
    sufficiency: str,
    observations: List[Dict[str, Any]],
) -> str:
    if sufficiency == "unable_to_determine":
        return "low"

    if relationship == "corroborated":
        return "high"

    if relationship == "conflicting":
        return "low"

    if (
        relationship == "single_source"
        and sufficiency == "sufficient"
    ):
        return "medium"

    if len(observations) > 1:
        return "medium"

    return "low"


def scope_for(
    observations: List[Dict[str, Any]],
) -> str:
    pages = {
        observation["page_url"]
        for observation in observations
        if observation["page_url"]
    }

    if len(pages) == 1:
        return "page"

    return "site"


def build_candidate(
    family: str,
    observations: List[Dict[str, Any]],
) -> Dict[str, Any]:

    observations = sorted(
        observations,
        key=lambda observation: (
            observation["skill"],
            observation["page_url"] or "",
            observation["signal"],
            observation["status"],
        ),
    )

    relationship = relationship_for(
        observations
    )

    sufficiency = sufficiency_for(
        observations
    )

    confidence = confidence_for(
        relationship,
        sufficiency,
        observations,
    )

    pages = sorted(
        {
            observation["page_url"]
            for observation in observations
            if observation["page_url"]
        }
    )

    skills = sorted(
        {
            observation["skill"]
            for observation in observations
        }
    )

    evidence = []

    seen_evidence = set()

    for observation in observations:
        evidence_key = (
            observation["skill"],
            observation["page_url"],
            observation["signal"],
            observation["status"],
            observation["source"],
        )

        if evidence_key in seen_evidence:
            continue

        seen_evidence.add(
            evidence_key
        )

        evidence.append(
            {
                "skill": observation["skill"],
                "page_url": observation["page_url"],
                "signal": observation["signal"],
                "status": observation["status"],
                "source": observation["source"],
            }
        )

    page_key = (
        normalize_key(pages[0])
        if pages
        else "site"
    )

    candidate_id = (
        f"candidate-{family}-{page_key}"
    )

    return {
        "candidate_id": candidate_id,
        "category": family,
        "issue": candidate_issue(
            family,
            observations,
        ),
        "scope": scope_for(
            observations
        ),
        "affected_pages": pages,
        "contributing_skills": skills,
        "evidence_relationship": relationship,
        "evidence_sufficiency": sufficiency,
        "confidence": confidence,
        "evidence": evidence,
        "limitations": [],
    }


def correlate(
    input_data: Any,
) -> Dict[str, Any]:

    skill_payloads = extract_skill_payloads(
        input_data
    )

    observations: List[Dict[str, Any]] = []

    for skill_name in sorted(
        skill_payloads
    ):
        observations.extend(
            collect_observations(
                skill_name,
                skill_payloads[skill_name],
            )
        )

    observations.sort(
        key=lambda observation: (
            issue_family(
                observation["category"],
                observation["signal"],
            ),
            observation["page_url"] or "",
            observation["skill"],
            observation["signal"],
        )
    )

    groups: List[
        List[Dict[str, Any]]
    ] = []

    for observation in observations:
        placed = False

        for group in groups:
            if any(
                compatible(
                    observation,
                    existing,
                )
                for existing in group
            ):
                group.append(
                    observation
                )
                placed = True
                break

        if not placed:
            groups.append(
                [observation]
            )

    findings: List[Dict[str, Any]] = []

    for group in groups:
        family = issue_family(
            group[0]["category"],
            group[0]["signal"],
        )

        findings.append(
            build_candidate(
                family,
                group,
            )
        )

    findings.sort(
        key=lambda finding: (
            finding["category"],
            finding["scope"],
            finding["affected_pages"],
            finding["candidate_id"],
        )
    )

    summary = empty_summary()

    summary["candidates_considered"] = len(
        groups
    )

    summary["correlated_findings"] = len(
        findings
    )

    for finding in findings:
        relationship = (
            finding[
                "evidence_relationship"
            ]
        )

        if relationship in summary:
            summary[relationship] += 1

    limitations: List[str] = []

    missing_skills = [
        skill
        for skill in SKILL_NAMES
        if skill not in skill_payloads
    ]

    if missing_skills:
        limitations.append(
            "Specialized evidence was unavailable for: "
            + ", ".join(
                sorted(missing_skills)
            )
        )

    if not observations:
        limitations.append(
            "No concrete specialized observations "
            "were available for correlation."
        )

    return {
        "schema_version":
            "evidence-correlator/v1",

        "summary":
            summary,

        "findings":
            findings,

        "limitations":
            limitations,
    }


def load_json(
    path: Path,
) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def write_json(
    path: Path,
    payload: Any,
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            ensure_ascii=False,
        )

        handle.write("\n")


def main(
    argv: List[str],
) -> int:

    if len(argv) not in {
        2,
        3,
    }:
        print(
            "Usage: python analyze_evidence.py "
            "input.json [output.json]",
            file=sys.stderr,
        )

        return 2

    input_path = Path(
        argv[1]
    )

    if not input_path.exists():
        print(
            f"Input file not found: {input_path}",
            file=sys.stderr,
        )

        return 2

    try:
        input_data = load_json(
            input_path
        )

        result = correlate(
            input_data
        )

    except json.JSONDecodeError as exc:
        print(
            f"Invalid JSON: {exc}",
            file=sys.stderr,
        )

        return 2

    except Exception as exc:
        print(
            f"Correlation failed: {exc}",
            file=sys.stderr,
        )

        return 1

    if len(argv) == 3:
        write_json(
            Path(argv[2]),
            result,
        )
    else:
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(sys.argv)
    )
