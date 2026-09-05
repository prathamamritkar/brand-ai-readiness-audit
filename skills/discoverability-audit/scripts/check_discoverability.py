import json
import sys
import urllib.robotparser
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def analyze_discoverability(url):
    findings = []
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # 1. Heuristic: AI Crawler Accessibility (robots.txt hygiene)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{base_url}/robots.txt")
    try:
        rp.read()
        # Checking universal AI agent mapping standards
        if not rp.can_fetch("GPTBot", url) or not rp.can_fetch("Google-Extended", url):
            findings.append({
                "id": "DISC-001",
                "title": "AI Crawlers Blocked via robots.txt",
                "severity": "critical",
                "evidence": "The robots.txt file explicitly disallows common AI user-agents (e.g., GPTBot) from extracting the DOM.",
                "suggested_action": {
                    "summary": "Update robots.txt directives to allow AI crawler user-agents to index public informational pages.",
                    "priority": "critical"
                }
            })
    except Exception:
        pass # If no robots.txt exists, assume accessible.

    # Fetch the raw DOM
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HackathonBot/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 2. Heuristic: Universal SEO Mapping Standards (JSON-LD)
        # We don't look for visual classes, we look for underlying structural truth
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        if not json_ld_scripts:
            findings.append({
                "id": "DISC-002",
                "title": "Missing Schema.org Structured Data",
                "severity": "high",
                "evidence": "0 <script type='application/ld+json'> tags found in the DOM. AI systems cannot explicitly map brand entities without this standard.",
                "suggested_action": {
                    "summary": "Embed JSON-LD structured data (e.g., Organization, Product) in the HTML <head> to definitively map entity properties.",
                    "priority": "high"
                }
            })

        # 3. Heuristic: JS-Render Gaps (Text-to-HTML Ratio)
        # Checking if facts are locked inside client-side JS rendering
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        
        visible_text = soup.get_text(separator=" ", strip=True)
        word_count = len(visible_text.split())
        
        if word_count < 100:
            findings.append({
                "id": "DISC-003",
                "title": "Severe Client-Side Rendering Dependency",
                "severity": "high",
                "evidence": f"The raw HTML payload contains only {word_count} readable words. Content is completely reliant on JS execution, making facts invisible to simple crawlers.",
                "suggested_action": {
                    "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so core facts exist in the static DOM payload.",
                    "priority": "high"
                }
            })

    except Exception as e:
         findings.append({
            "id": "DISC-ERR",
            "title": "DOM Extraction Failure",
            "severity": "critical",
            "evidence": f"Failed to fetch the target URL: {str(e)}",
            "suggested_action": {
                "summary": "Verify the URL is publicly accessible and not blocking automated HTTP requests.",
                "priority": "critical"
            }
        })

    return findings

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Target URL is required."}))
        sys.exit(1)
        
    target_url = sys.argv[1]
    results = analyze_discoverability(target_url)
    
    # Outputs the exact JSON format required by the orchestrator schema
    print(json.dumps(results, indent=2))