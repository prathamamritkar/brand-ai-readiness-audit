"""
Deterministic Recommendation Engine.

Transforms Evidence Correlator findings into actionable,
evidence-backed recommendations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "recommendation-engine/v1"

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

CONFIDENCE_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


CATEGORY_GUIDANCE = {
    "entity_identity": {
        "title": "Strengthen entity identity signals",
        "root_cause": (
            "The available evidence indicates that important organization "
            "or product identity signals are incomplete or unclear."
        ),
        "action": (
            "Review the affected page and strengthen consistent, "
            "machine-readable and human-readable identity signals for the "
            "organization, product, or service."
        ),
        "outcome": (
            "Important entities and their relationships should be easier "
            "for automated systems and users to interpret consistently."
        ),
        "verification": (
            "Re-run the relevant identity and machine-readability checks "
            "and confirm that the previously observed gaps are addressed."
        ),
    },
    "machine_structure": {
        "title": "Improve machine-readable structure",
        "root_cause": (
            "The evidence indicates that structured machine-readable "
            "information is missing or insufficient."
        ),
        "action": (
            "Review the affected page and add or improve appropriate "
            "machine-readable representations for the information already "
            "present on the page."
        ),
        "outcome": (
            "Important page information should have clearer structured "
            "representations for automated interpretation."
        ),
        "verification": (
            "Re-run the machine-readability audit and verify that the "
            "relevant structured signals are present and consistent with "
            "the visible page content."
        ),
    },
    "semantic_structure": {
        "title": "Improve semantic page structure",
        "root_cause": (
            "The evidence indicates that important content lacks clear "
            "semantic organization."
        ),
        "action": (
            "Review headings, content sections, labels, and other semantic "
            "structure on the affected page so that important information "
            "has clear and meaningful organization."
        ),
        "outcome": (
            "Users and automated systems should be able to interpret the "
            "page's information hierarchy more reliably."
        ),
        "verification": (
            "Re-run the semantic structure checks and verify that key "
            "content has an understandable hierarchy and meaningful "
            "structural signals."
        ),
    },
    "engagement_pathway": {
        "title": "Clarify the primary engagement pathway",
        "root_cause": (
            "The evidence indicates that the primary action or engagement "
            "pathway is unclear, missing, or difficult to identify."
        ),
        "action": (
            "Review the affected page and make the intended primary "
            "engagement action clear, visible, and contextually connected "
            "to the page's purpose."
        ),
        "outcome": (
            "Users and agents should have a clearer path from relevant "
            "information to the intended next action."
        ),
        "verification": (
            "Re-run the engagement audit and verify that the primary "
            "pathway can be identified from the page evidence."
        ),
    },
    "navigation_pathway": {
        "title": "Improve navigation and discoverability pathways",
        "root_cause": (
            "The evidence indicates that important navigation or "
            "discoverability pathways are incomplete or unclear."
        ),
        "action": (
            "Review the affected navigation pathways and ensure that "
            "important related content can be reached through clear, "
            "contextually meaningful links."
        ),
        "outcome": (
            "Important pages and relationships should be easier to discover "
            "and navigate."
        ),
        "verification": (
            "Re-run the navigation checks and verify that the relevant "
            "pages are connected through meaningful pathways."
        ),
    },
    "render_observability": {
        "title": "Improve rendered content observability",
        "root_cause": (
            "The evidence indicates that important content or structure "
            "may not be reliably observable in the rendered experience."
        ),
        "action": (
            "Review the affected page and ensure that important information "
            "and interaction elements are available in the rendered page "
            "state without relying on unsupported assumptions."
        ),
        "outcome": (
            "Important page information should remain observable to "
            "render-aware auditing and automated interpretation."
        ),
        "verification": (
            "Re-run the render observability audit and compare the rendered "
            "evidence with the intended page content."
        ),
    },
    "freshness_signal": {
        "title": "Strengthen freshness signals",
        "root_cause": (
            "The evidence indicates that available freshness or update "
            "signals are incomplete, inconsistent, or difficult to verify."
        ),
        "action": (
            "Review the affected content and ensure that legitimate update "
            "signals accurately reflect the content's current state."
        ),
        "outcome": (
            "Automated systems and users should have clearer evidence about "
            "the recency and maintenance of relevant information."
        ),
        "verification": (
            "Re-run the freshness checks and verify that update signals "
            "are present, consistent, and supported by the page evidence."
        ),
    },
}


def load_input(path: str) -> dict[str, Any]:
    """Load a JSON input file."""
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")

    return data


def normalize(value: Any) -> str:
    """Normalize a value for deterministic comparisons."""
    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def valid_confidence(value: Any) -> str:
    """Return a valid confidence value."""
    value = normalize(value)

    if value in CONFIDENCE_ORDER:
        return value

    return "low"


def valid_sufficiency(value: Any) -> str:
    """Return a valid evidence sufficiency value."""
    value = normalize(value)

    allowed = {
        "sufficient",
        "insufficient",
        "unable_to_determine",
    }

    return value if value in allowed else "unable_to_determine"


def priority_from_finding(finding: dict[str, Any]) -> str:
    """
    Determine priority conservatively.

    Explicit valid severity takes precedence. Otherwise derive priority
    from evidence sufficiency, confidence, and scope.
    """
    severity = normalize(finding.get("severity"))

    if severity in PRIORITY_ORDER:
        return severity

    confidence = valid_confidence(finding.get("confidence"))
    sufficiency = valid_sufficiency(finding.get("evidence_sufficiency"))
    scope = normalize(finding.get("scope"))

    if (
        confidence == "high"
        and sufficiency == "sufficient"
        and scope == "site"
    ):
        return "high"

    if confidence == "high" and sufficiency == "sufficient":
        return "high"

    if confidence == "medium" and sufficiency == "sufficient":
        return "medium"

    return "low"


def extract_findings(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract finding objects from Evidence Correlator output."""
    findings = data.get("findings", [])

    if not isinstance(findings, list):
        return []

    return [
        item
        for item in findings
        if isinstance(item, dict)
    ]


def guidance_for(category: str) -> dict[str, str]:
    """Return deterministic guidance for a category."""
    category_key = normalize(category)

    if category_key in CATEGORY_GUIDANCE:
        return CATEGORY_GUIDANCE[category_key]

    return {
        "title": "Review the identified audit issue",
        "root_cause": (
            "The available evidence indicates that the identified issue "
            "requires review."
        ),
        "action": (
            "Review the supplied evidence for the affected scope and "
            "address the specific gap identified by the contributing "
            "audit skill."
        ),
        "outcome": (
            "The identified evidence gap should be reduced without "
            "introducing unsupported assumptions."
        ),
        "verification": (
            "Re-run the relevant audit checks and verify that the "
            "identified evidence gap has been addressed."
        ),
    }


def build_recommendation(finding: dict[str, Any]) -> dict[str, Any]:
    """Convert one finding into one recommendation."""
    category = str(
        finding.get("category") or "unknown"
    ).strip()

    confidence = valid_confidence(finding.get("confidence"))
    sufficiency = valid_sufficiency(
        finding.get("evidence_sufficiency")
    )
    priority = priority_from_finding(finding)

    guidance = guidance_for(category)

    candidate_id = str(
        finding.get("candidate_id") or "unknown-candidate"
    ).strip()

    scope = str(
        finding.get("scope") or "site"
    ).strip()

    affected_pages = finding.get("affected_pages", [])
    if not isinstance(affected_pages, list):
        affected_pages = []

    evidence = finding.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []

    limitations = finding.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []

    if sufficiency != "sufficient":
        title = f"Verify: {guidance['title']}"

        problem = (
            "The available evidence is not sufficient to make a "
            "definitive remediation claim."
        )

        action = (
            "Verify the underlying observation and collect the missing "
            "evidence before applying a remediation."
        )

        expected_outcome = (
            "A verified evidence base should clarify whether remediation "
            "is actually required."
        )

        verification = (
            "Re-run the relevant audit checks and confirm whether the "
            "observed issue is reproducible."
        )
    else:
        title = guidance["title"]

        problem = str(
            finding.get("issue")
            or "The audit identified an issue requiring review."
        ).strip()

        action = guidance["action"]
        expected_outcome = guidance["outcome"]
        verification = guidance["verification"]

    recommendation_id = (
        "recommendation-"
        + normalize(candidate_id).replace(" ", "-")
    )

    return {
        "recommendation_id": recommendation_id,
        "candidate_id": candidate_id,
        "category": category,
        "priority": priority,
        "title": title,
        "problem": problem,
        "root_cause": guidance["root_cause"],
        "action": action,
        "expected_outcome": expected_outcome,
        "verification": verification,
        "scope": scope,
        "affected_pages": sorted(
            {
                str(page).strip()
                for page in affected_pages
                if str(page).strip()
            }
        ),
        "confidence": confidence,
        "evidence_sufficiency": sufficiency,
        "evidence": evidence,
        "limitations": limitations,
    }


def sort_recommendations(
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort recommendations deterministically."""
    return sorted(
        recommendations,
        key=lambda item: (
            PRIORITY_ORDER.get(item["priority"], 99),
            CONFIDENCE_ORDER.get(item["confidence"], 99),
            normalize(item["category"]),
            normalize(item["candidate_id"]),
        ),
    )


def build_output(data: dict[str, Any]) -> dict[str, Any]:
    """Build the complete Recommendation Engine output."""
    findings = extract_findings(data)

    recommendations = [
        build_recommendation(finding)
        for finding in findings
    ]

    recommendations = sort_recommendations(recommendations)

    summary = {
        "recommendations_generated": len(recommendations),
        "high_priority": sum(
            item["priority"] == "high"
            for item in recommendations
        ),
        "medium_priority": sum(
            item["priority"] == "medium"
            for item in recommendations
        ),
        "low_priority": sum(
            item["priority"] == "low"
            for item in recommendations
        ),
        "verification_required": sum(
            item["evidence_sufficiency"] != "sufficient"
            for item in recommendations
        ),
    }

    limitations = data.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []

    return {
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "recommendations": recommendations,
        "limitations": limitations,
    }


def main() -> None:
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print(
            "Usage: python recommend.py input.json [output.json]",
            file=sys.stderr,
        )
        raise SystemExit(1)

    input_path = sys.argv[1]
    output = build_output(load_input(input_path))

    rendered = json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    )

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
        output_path.write_text(
            rendered + "\n",
            encoding="utf-8",
        )
    else:
        print(rendered)


if __name__ == "__main__":
    main()