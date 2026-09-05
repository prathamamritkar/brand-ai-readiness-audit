import json
import sys
import requests
from bs4 import BeautifulSoup

def analyze_engagement(url):
    findings = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HackathonBot/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Heuristic: Structural Orientation (Heading Hierarchy)
        # We don't care what the site looks like, we care about the semantic map.
        h1_tags = soup.find_all("h1")
        if len(h1_tags) == 0:
            findings.append({
                "id": "ENG-001",
                "title": "Missing Primary <h1> Tag",
                "severity": "high",
                "evidence": "0 <h1> tags found in the DOM. The page lacks a definitive structural title, causing weak on-site orientation for both users and machines.",
                "suggested_action": {
                    "summary": "Wrap the core value proposition or page title in a single <h1> tag above the fold.",
                    "priority": "high"
                }
            })
        elif len(h1_tags) > 1:
            findings.append({
                "id": "ENG-002",
                "title": "Conflicting <h1> Hierarchy",
                "severity": "medium",
                "evidence": f"Found {len(h1_tags)} <h1> tags. Multiple primary headings fracture the semantic context and confuse visitor orientation.",
                "suggested_action": {
                    "summary": "Consolidate the page structure to use a single <h1> tag, demoting secondary sections to <h2> or <h3>.",
                    "priority": "medium"
                }
            })

        # 2. Heuristic: Context Retention (Wall of Text / Readability)
        # Checking for overwhelmingly long paragraphs that cause user bounce.
        paragraphs = soup.find_all("p")
        massive_paragraphs = [p for p in paragraphs if len(p.get_text(strip=True).split()) > 150]
        
        if len(massive_paragraphs) > 2:
            findings.append({
                "id": "ENG-003",
                "title": "Poor Readability: Massive Text Blocks",
                "severity": "medium",
                "evidence": f"Detected {len(massive_paragraphs)} paragraph (<p>) tags containing over 150 words each without structural breakers.",
                "suggested_action": {
                    "summary": "Break up dense text blocks using bullet points, short paragraphs, or <h2>/<h3> subheadings to retain visitor context.",
                    "priority": "medium"
                }
            })

        # 3. Heuristic: Accessible Context (Image Alt Text)
        # Crucial for human engagement (screen readers) and AI context.
        images = soup.find_all("img")
        missing_alt = [img for img in images if not img.get("alt")]
        
        if images and (len(missing_alt) / len(images)) > 0.5:
            findings.append({
                "id": "ENG-004",
                "title": "High Volume of Missing Image Context",
                "severity": "medium",
                "evidence": f"{len(missing_alt)} out of {len(images)} <img> tags are missing 'alt' attributes, locking context away from screen readers and fallback states.",
                "suggested_action": {
                    "summary": "Add descriptive 'alt' text to all informative images to ensure contextual retention if rendering fails or for accessibility.",
                    "priority": "medium"
                }
            })

    except Exception as e:
        findings.append({
            "id": "ENG-ERR",
            "title": "DOM Extraction Failure",
            "severity": "critical",
            "evidence": f"Failed to parse the target URL for engagement metrics: {str(e)}",
            "suggested_action": {
                "summary": "Ensure the URL is resolving correctly and returning valid HTML.",
                "priority": "critical"
            }
        })

    return findings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Target URL is required."}))
        sys.exit(1)
        
    target_url = sys.argv[1]
    results = analyze_engagement(target_url)
    print(json.dumps(results, indent=2))