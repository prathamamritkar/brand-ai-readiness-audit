import sys
import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

def analyze_performance(soup, response_headers, url, base_url):
    """
    Analyzes page performance signals that affect AI crawl budget and user bounce rates.
    """
    findings = []
    
    # PA-001: Excessive External Scripts
    external_scripts = []
    parsed_base = urlparse(base_url)
    for script in soup.find_all('script', src=True):
        src = script.get('src', '')
        parsed_src = urlparse(src)
        if parsed_src.netloc and parsed_src.netloc != parsed_base.netloc:
            external_scripts.append(src)
    
    if len(external_scripts) > 15:
        findings.append({
            "id": "PA-001",
            "title": "Excessive External Scripts",
            "severity": "high",
            "evidence": f"{len(external_scripts)} external scripts detected. Excessive scripts increase page load time and crawl cost.",
            "suggested_action": {
                "summary": "Review and remove unnecessary external scripts. Consider bundling or deferring scripts.",
                "priority": "high"
            }
        })
        
    # PA-002: Render-Blocking Resources
    head = soup.find('head')
    render_blocking_count = 0
    if head:
        stylesheets = head.find_all('link', rel=lambda x: x and 'stylesheet' in [r.lower() for r in (x if isinstance(x, list) else [x])])
        scripts = head.find_all('script')
        for script in scripts:
            if not script.has_attr('async') and not script.has_attr('defer') and script.has_attr('src'):
                render_blocking_count += 1
        render_blocking_count += len(stylesheets)
        
        if render_blocking_count > 5:
            findings.append({
                "id": "PA-002",
                "title": "Render-Blocking Resources",
                "severity": "high",
                "evidence": f"{render_blocking_count} render-blocking resources in <head>.",
                "suggested_action": {
                    "summary": "Defer non-critical JavaScript and CSS to speed up the initial render.",
                    "priority": "high"
                }
            })

    # PA-003: Excessive Page Weight (Inline)
    html_size_kb = len(str(soup)) / 1024
    if html_size_kb > 500:
        findings.append({
            "id": "PA-003",
            "title": "Excessive Page Weight (Inline)",
            "severity": "medium",
            "evidence": f"HTML document is {html_size_kb:.1f}KB. Heavy pages reduce AI crawl efficiency.",
            "suggested_action": {
                "summary": "Minify HTML and remove unnecessary inline data or comments.",
                "priority": "medium"
            }
        })
        
    # PA-004: No Lazy Loading on Images
    images = soup.find_all('img')
    images_without_lazy = 0
    for img in images[3:]:
        if img.get('loading') != 'lazy':
            images_without_lazy += 1
            
    if images_without_lazy > 5:
        findings.append({
            "id": "PA-004",
            "title": "No Lazy Loading on Images",
            "severity": "medium",
            "evidence": f"{images_without_lazy}/{len(images)} images lack loading='lazy'.",
            "suggested_action": {
                "summary": "Add loading='lazy' attribute to images that are below the fold.",
                "priority": "medium"
            }
        })
        
    # PA-005: Inline CSS Bloat
    styles = soup.find_all('style')
    total_style_size_kb = sum(len(style.string or '') for style in styles) / 1024
    if total_style_size_kb > 50:
        findings.append({
            "id": "PA-005",
            "title": "Inline CSS Bloat",
            "severity": "medium",
            "evidence": f"{total_style_size_kb:.1f}KB of inline CSS across {len(styles)} <style> blocks.",
            "suggested_action": {
                "summary": "Extract large inline CSS blocks into external stylesheets.",
                "priority": "medium"
            }
        })
        
    # PA-006: No Resource Hints
    resource_hints = soup.find_all('link', rel=lambda x: x and any(hint in (x if isinstance(x, list) else [x]) for hint in ['preconnect', 'dns-prefetch', 'preload']))
    if not resource_hints:
        findings.append({
            "id": "PA-006",
            "title": "No Resource Hints",
            "severity": "medium",
            "evidence": "No resource hints found. Adding preconnect/preload hints can improve load performance.",
            "suggested_action": {
                "summary": "Use <link rel='preconnect'> or preload for critical third-party origins or key resources.",
                "priority": "medium"
            }
        })
        
    # PA-007: [Proactive] No Web App Manifest
    manifest = soup.find('link', rel=lambda x: x and 'manifest' in (x if isinstance(x, list) else [x]))
    if not manifest:
        findings.append({
            "id": "PA-007",
            "title": "[Proactive] No Web App Manifest",
            "severity": "medium",
            "evidence": "No web app manifest linked. Adding a manifest enables PWA features and signals a modern, performant site.",
            "suggested_action": {
                "summary": "Create and link a Web App Manifest.",
                "priority": "medium"
            }
        })
        
    return findings

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_performance.py <url>")
        sys.exit(1)
        
    test_url = sys.argv[1]
    try:
        response = requests.get(test_url, timeout=10)
        test_soup = BeautifulSoup(response.content, 'html.parser')
        results = analyze_performance(test_soup, response.headers, test_url, test_url)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error fetching URL: {e}")
