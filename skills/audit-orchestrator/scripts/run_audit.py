import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[2]

SITE_INTELLIGENCE = (
    ROOT / "site-intelligence" / "scripts" / "crawl_site.py"
)

SPECIALISTS = {
    "machine-readability": (
        ROOT / "machine-readability" / "scripts"
        / "analyze_machine_readability.py"
    ),
    "engagement-audit": (
        ROOT / "engagement-audit" / "scripts"
        / "analyze_engagement.py"
    ),
    "crawl-render-audit": (
        ROOT / "crawl-render-audit" / "scripts"
        / "analyze_crawl_render.py"
    ),
    "freshness-corroboration": (
        ROOT / "freshness-corroboration" / "scripts"
        / "analyze_freshness.py"
    ),
    "entity-trust": (
        ROOT / "entity-trust" / "scripts"
        / "analyze_entity.py"
    ),
}

CORRELATOR = (
    ROOT / "evidence-correlator" / "scripts"
    / "analyze_evidence.py"
)

RECOMMENDER = (
    ROOT / "recommendation-engine" / "scripts"
    / "recommend.py"
)


def run_json_script(
    script: Path,
    input_path: Path,
    output_path: Path,
) -> None:
    """Run a JSON-in/JSON-out skill script."""
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            str(input_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or f"Skill failed with exit code {completed.returncode}"
        )

    output = completed.stdout.strip()

    if not output:
        raise RuntimeError("Skill returned no JSON output")

    output_path.write_text(
        output + "\n",
        encoding="utf-8",
    )

    json.loads(output)


def run_site_intelligence(
    url: str,
    output_path: Path,
) -> None:
    """Collect the shared Evidence Bundle."""
    completed = subprocess.run(
        [
            sys.executable,
            str(SITE_INTELLIGENCE),
            url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "Site Intelligence failed"
        )

    output = completed.stdout.strip()

    if not output:
        raise RuntimeError(
            "Site Intelligence returned no evidence"
        )

    output_path.write_text(
        output + "\n",
        encoding="utf-8",
    )

    json.loads(output)


def run_specialists(
    evidence_path: Path,
    workdir: Path,
) -> Dict[str, Any]:
    """Run all independent specialist skills."""
    outputs: Dict[str, Any] = {}

    for skill_name, script in SPECIALISTS.items():
        if not script.exists():
            outputs[skill_name] = {
                "status": "unavailable",
                "reason": "skill script not present",
            }
            continue

        output_path = workdir / f"{skill_name}.json"

        try:
            run_json_script(
                script,
                evidence_path,
                output_path,
            )

            outputs[skill_name] = {
                "status": "completed",
                "output": json.loads(
                    output_path.read_text(
                        encoding="utf-8"
                    )
                ),
            }

        except Exception as exc:
            outputs[skill_name] = {
                "status": "failed",
                "reason": str(exc),
            }

    return outputs


def build_correlator_input(
    specialist_outputs: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the Evidence Correlator input contract."""
    return {
        "skills": {
            name: payload["output"]
            for name, payload in specialist_outputs.items()
            if payload.get("status") == "completed"
        }
    }


def build_recommendation_input(
    correlation: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the Recommendation Engine input contract."""
    return correlation


def build_report(
    url: str,
    evidence: Dict[str, Any],
    specialist_outputs: Dict[str, Any],
    correlation: Dict[str, Any],
    recommendations: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the marketplace final report."""
    findings = correlation.get("findings", [])

    recommendation_list = recommendations.get(
        "recommendations",
        [],
    )

    status = [
        {
            "skill": "site-intelligence",
            "status": "completed",
        }
    ]

    status.extend(
        {
            "skill": name,
            "status": payload["status"],
        }
        for name, payload in specialist_outputs.items()
    )

    status.append(
        {
            "skill": "evidence-correlator",
            "status": "completed",
        }
    )

    status.append(
        {
            "skill": "recommendation-engine",
            "status": "completed",
        }
    )

    priority_counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for recommendation in recommendation_list:
        priority = recommendation.get("priority")

        if priority in priority_counts:
            priority_counts[priority] += 1

    limitations = []

    limitations.extend(
        evidence.get("crawl", {}).get(
            "limitations",
            [],
        )
    )

    limitations.extend(
        correlation.get(
            "limitations",
            [],
        )
    )

    limitations.extend(
        recommendations.get(
            "limitations",
            [],
        )
    )

    for name, payload in specialist_outputs.items():
        if payload["status"] == "completed":
            limitations.extend(
                f"{name}: {item}"
                for item in payload.get("output", {}).get(
                    "limitations",
                    [],
                )
            )
        else:
            limitations.append(
                f"{name}: {payload.get('reason', 'unavailable')}"
            )
    crawl_started = evidence.get(
        "crawl",
        {},
    ).get(
        "started_at_unix"
    )

    if crawl_started is not None:
        audited_at = datetime.fromtimestamp(
            crawl_started,
            tz=timezone.utc,
        ).isoformat()
    else:
        audited_at = None

    return {
        "schema_version": (
            "brand-ai-readiness-audit/v1"
        ),
        "site": {
            "url": url,
            "audited_at": audited_at,
        },
        "summary": {
            "pages_audited": len(
                evidence.get("pages", [])
            ),
            "findings": len(findings),
            "recommendations": len(
                recommendation_list
            ),
            "high_priority": priority_counts["high"],
            "medium_priority": priority_counts["medium"],
            "low_priority": priority_counts["low"],
        },
        "skill_status": status,
        "findings": findings,
        "recommendations": recommendation_list,
        "limitations": sorted(
            set(
                str(item)
                for item in limitations
            )
        ),
    }


def audit(url: str) -> Dict[str, Any]:
    """Execute the complete marketplace audit pipeline."""
    with tempfile.TemporaryDirectory(
        prefix="brand_ai_audit_"
    ) as temp:
        workdir = Path(temp)

        evidence_path = workdir / "evidence.json"

        run_site_intelligence(
            url,
            evidence_path,
        )

        evidence = json.loads(
            evidence_path.read_text(
                encoding="utf-8"
            )
        )

        specialist_outputs = run_specialists(
            evidence_path,
            workdir,
        )

        correlator_input = (
            build_correlator_input(
                specialist_outputs
            )
        )

        correlator_input_path = (
            workdir / "correlator_input.json"
        )

        correlator_input_path.write_text(
            json.dumps(
                correlator_input,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        correlation_path = (
            workdir / "correlation.json"
        )

        if CORRELATOR.exists():
            run_json_script(
                CORRELATOR,
                correlator_input_path,
                correlation_path,
            )

            correlation = json.loads(
                correlation_path.read_text(
                    encoding="utf-8"
                )
            )

            correlator_status = "completed"

        else:
            correlation = {
                "findings": [],
                "limitations": [
                    "Evidence Correlator is not "
                    "available in this checkout."
                ],
            }

            correlator_status = "unavailable"

        if correlator_status == "unavailable":
            recommendations = {
                "recommendations": [],
                "limitations": [
                    "Recommendations require "
                    "Evidence Correlator output."
                ],
            }

            recommender_status = "unavailable"

        else:
            recommendation_input = (
                build_recommendation_input(
                    correlation
                )
            )

            recommendation_input_path = (
                workdir / "recommendation_input.json"
            )

            recommendation_input_path.write_text(
                json.dumps(
                    recommendation_input,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            recommendation_path = (
                workdir / "recommendations.json"
            )

            try:
                run_json_script(
                    RECOMMENDER,
                    recommendation_input_path,
                    recommendation_path,
                )

                recommendations = json.loads(
                    recommendation_path.read_text(
                        encoding="utf-8"
                    )
                )

                recommender_status = "completed"

            except Exception as exc:
                recommendations = {
                    "recommendations": [],
                    "limitations": [
                        f"Recommendation Engine: {exc}"
                    ],
                }

                recommender_status = "failed"

        report = build_report(
            url,
            evidence,
            specialist_outputs,
            correlation,
            recommendations,
        )

        for item in report["skill_status"]:
            if item["skill"] == "evidence-correlator":
                item["status"] = correlator_status

            if item["skill"] == "recommendation-engine":
                item["status"] = recommender_status

        return report


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python run_audit.py <public-url>",
            file=sys.stderr,
        )
        return 2

    try:
        report = audit(sys.argv[1])

    except Exception as exc:
        print(
            f"Audit failed: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
