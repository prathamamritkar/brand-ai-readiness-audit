import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_audit


class TestAuditOrchestrator(unittest.TestCase):

    def test_build_correlator_input_uses_completed_skills_only(self):
        outputs = {
            "machine-readability": {
                "status": "completed",
                "output": {
                    "findings": [
                        {"category": "machine_structure"}
                    ]
                },
            },
            "engagement-audit": {
                "status": "failed",
                "reason": "test failure",
            },
            "entity-trust": {
                "status": "completed",
                "output": {
                    "findings": [
                        {"category": "entity_identity"}
                    ]
                },
            },
        }

        result = run_audit.build_correlator_input(outputs)

        self.assertEqual(
            set(result["skills"].keys()),
            {
                "machine-readability",
                "entity-trust",
            },
        )

    def test_build_correlator_input_preserves_payload(self):
        payload = {
            "schema_version": "test/v1",
            "findings": [
                {
                    "category": "machine_structure",
                    "signal": "missing_jsonld",
                }
            ],
        }

        outputs = {
            "machine-readability": {
                "status": "completed",
                "output": payload,
            }
        }

        result = run_audit.build_correlator_input(outputs)

        self.assertEqual(
            result["skills"]["machine-readability"],
            payload,
        )

    def test_build_report_counts_findings_and_recommendations(self):
        evidence = {
            "pages": [
                {"url": "https://example.com"}
            ],
            "crawl": {
                "started_at_unix": 0,
                "limitations": [],
            },
        }

        specialist_outputs = {
            "machine-readability": {
                "status": "completed",
            }
        }

        correlation = {
            "findings": [
                {"candidate_id": "candidate-1"},
                {"candidate_id": "candidate-2"},
            ],
            "limitations": [],
        }

        recommendations = {
            "recommendations": [
                {"priority": "high"},
                {"priority": "medium"},
                {"priority": "low"},
                {"priority": "high"},
            ],
            "limitations": [],
        }

        report = run_audit.build_report(
            "https://example.com",
            evidence,
            specialist_outputs,
            correlation,
            recommendations,
        )

        self.assertEqual(
            report["summary"]["pages_audited"],
            1,
        )

        self.assertEqual(
            report["summary"]["findings"],
            2,
        )

        self.assertEqual(
            report["summary"]["recommendations"],
            4,
        )

        self.assertEqual(
            report["summary"]["high_priority"],
            2,
        )

        self.assertEqual(
            report["summary"]["medium_priority"],
            1,
        )

        self.assertEqual(
            report["summary"]["low_priority"],
            1,
        )

        self.assertEqual(
            report["site"]["audited_at"],
            "1970-01-01T00:00:00+00:00",
        )

    def test_build_report_deduplicates_limitations(self):
        evidence = {
            "pages": [],
            "crawl": {
                "started_at_unix": 0,
                "limitations": [
                    "crawl limitation",
                ],
            },
        }

        specialist_outputs = {
            "machine-readability": {
                "status": "failed",
                "reason": "analysis failed",
            }
        }

        correlation = {
            "findings": [],
            "limitations": [
                "correlation limitation",
            ],
        }

        recommendations = {
            "recommendations": [],
            "limitations": [
                "recommendation limitation",
            ],
        }

        report = run_audit.build_report(
            "https://example.com",
            evidence,
            specialist_outputs,
            correlation,
            recommendations,
        )

        self.assertEqual(
            len(report["limitations"]),
            4,
        )

        self.assertIn(
            "crawl limitation",
            report["limitations"],
        )

        self.assertIn(
            "correlation limitation",
            report["limitations"],
        )

        self.assertIn(
            "recommendation limitation",
            report["limitations"],
        )

        self.assertIn(
            "machine-readability: analysis failed",
            report["limitations"],
        )

    def test_missing_correlator_produces_graceful_degradation(self):
        evidence = {
            "pages": [],
            "crawl": {
                "started_at_unix": 0,
                "limitations": [],
            },
        }

        specialist_outputs = {
            "machine-readability": {
                "status": "completed",
                "output": {
                    "findings": [],
                },
            }
        }

        def mock_site_intelligence(
            url,
            output_path,
        ):
            output_path.write_text(
                json.dumps(evidence),
                encoding="utf-8",
            )

        with patch.object(
            run_audit,
            "run_site_intelligence",
            side_effect=mock_site_intelligence,
        ), patch.object(
            run_audit,
            "run_specialists",
            return_value=specialist_outputs,
        ), patch.object(
            run_audit,
            "CORRELATOR",
            Path("nonexistent-correlator.py"),
        ):

            result = run_audit.audit(
                "https://example.com"
            )

        correlator_status = next(
            item["status"]
            for item in result["skill_status"]
            if item["skill"] == "evidence-correlator"
        )

        recommender_status = next(
            item["status"]
            for item in result["skill_status"]
            if item["skill"] == "recommendation-engine"
        )

        self.assertEqual(
            correlator_status,
            "unavailable",
        )

        self.assertEqual(
            recommender_status,
            "unavailable",
        )

        self.assertEqual(
            result["findings"],
            [],
        )

        self.assertEqual(
            result["recommendations"],
            [],
        )


if __name__ == "__main__":
    unittest.main()