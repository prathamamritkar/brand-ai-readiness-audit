import json
import sys
import subprocess
from datetime import datetime, timezone

def run_marketplace(url):
    # Defining the strict order of execution for AI contextual learning
    skills_to_run = [
        "skills/discoverability-audit/scripts/check_discoverability.py",
        "skills/engagement-audit/scripts/check_engagement.py"
    ]

    all_findings = []

    # Execute each skill independently and aggregate the findings
    for script_path in skills_to_run:
        try:
            # Running as a subprocess to keep skills modular and decoupled
            result = subprocess.run(
                [sys.executable, script_path, url],
                capture_output=True,
                text=True,
                timeout=60 # Ensures strict adherence to the <5 minute total runtime rule
            )
            
            if result.stdout.strip():
                # Load the JSON array outputted by the individual skill
                skill_findings = json.loads(result.stdout.strip())
                all_findings.extend(skill_findings)
                
        except Exception as e:
            # If a single skill fails, the orchestrator continues running
            pass

    # Calculate severity metrics for the summary object
    critical_count = sum(1 for f in all_findings if f.get("severity") == "critical")
    high_count = sum(1 for f in all_findings if f.get("severity") == "high")
    medium_count = sum(1 for f in all_findings if f.get("severity") == "medium")

    # Construct the final report matching the mandatory hackathon schema
    report = {
        "site": url,
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_findings": len(all_findings),
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count
        },
        "findings": all_findings
    }

    return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Target URL is required."}))
        sys.exit(1)
        
    target_url = sys.argv[1]
    final_report = run_marketplace(target_url)
    
    # Emit the final structured report
    print(json.dumps(final_report, indent=2))