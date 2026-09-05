import sys
import re
import json
import urllib.robotparser
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

def _get_visible_text(soup):
    import copy
    soup_copy = copy.copy(soup)
    for tag in soup_copy(["script", "style", "noscript", "svg", "head", "title", "meta", "[document]"]):
        tag.decompose()
    return soup_copy.get_text(separator=' ', strip=True)

def analyze_crawl_render(soup, robots_parser, response_headers, url, base_url):
    findings = []
    
    # Phase A — Crawl Access
    
    # CR-001
    ai_bots = ['GPTBot', 'Google-Extended', 'PerplexityBot', 'ClaudeBot', 'Amazonbot']
    blocked_bots = []
    if robots_parser:
        for bot in ai_bots:
            if not robots_parser.can_fetch(bot, url):
                blocked_bots.append(bot)
    
    if blocked_bots:
        findings.append({
            "id": "CR-001",
            "title": "AI Crawlers Blocked via robots.txt",
            "severity": "critical",
            "evidence": f"The following AI bots are blocked by robots.txt: {', '.join(blocked_bots)}.",
            "suggested_action": {
                "summary": "Remove blocks for AI-specific user agents in robots.txt if you want your content to be ingested by their models.",
                "priority": "critical"
            }
        })
    
    # CR-002
    meta_robots_tags = soup.find_all("meta", attrs={"name": re.compile(r"robots|googlebot|bingbot|gptbot", re.I)})
    blocked_directives = []
    for tag in meta_robots_tags:
        content = tag.get("content", "").lower()
        if any(d in content for d in ["noindex", "nofollow", "nosnippet", "none"]):
            name = tag.get("name", "robots")
            blocked_directives.append(f"<meta name='{name}' content='{content}'>")
            
    if blocked_directives:
        findings.append({
            "id": "CR-002",
            "title": "Meta Robots Noindex/Nosnippet",
            "severity": "critical",
            "evidence": f"Found blocking directives: {', '.join(blocked_directives)}.",
            "suggested_action": {
                "summary": "Remove noindex/nosnippet directives if the content is meant to be visible to search engines and AI systems.",
                "priority": "critical"
            }
        })
        
    # Phase B — JS Rendering Gap
    
    # CR-003 & CR-004 & CR-006
    visible_text = _get_visible_text(soup)
    words = visible_text.split()
    word_count = len(words)
    
    external_scripts = soup.find_all("script", src=True)
    script_count = len(external_scripts)
    
    raw_html = str(soup)
    framework_markers = ['__NEXT_DATA__', '__NUXT__', 'window.__INITIAL_STATE__', 'data-reactroot', 'data-server-rendered']
    detected_markers = [m for m in framework_markers if m in raw_html]
    
    ssr_detected = len(detected_markers) > 0
    
    if ssr_detected:
        findings.append({
            "id": "CR-006",
            "title": "[Proactive] SSR Framework Detected",
            "severity": "medium",
            "evidence": f"Found SSR markers in HTML: {', '.join(detected_markers)}.",
            "suggested_action": {
                "summary": "Framework supports SSR. Ensure critical content is rendered server-side.",
                "priority": "medium"
            }
        })
        
    if word_count < 100:
        evidence = f"Raw HTML contains only {word_count} readable words — core facts entirely dependent on client-side JavaScript execution."
        if not ssr_detected:
            evidence += " No SSR framework markers were detected."
        findings.append({
            "id": "CR-003",
            "title": "Severe JS Rendering Dependency",
            "severity": "high",
            "evidence": evidence,
            "suggested_action": {
                "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so basic crawlers can access the content without executing JS.",
                "priority": "high"
            }
        })
    elif 100 <= word_count <= 300 and script_count > 5:
        evidence = f"{word_count} words in static HTML with {script_count} external scripts suggests partial SSR but heavy JS dependency."
        if not ssr_detected:
            evidence += " No SSR framework markers were detected."
        findings.append({
            "id": "CR-004",
            "title": "Moderate JS Content Risk",
            "severity": "medium",
            "evidence": evidence,
            "suggested_action": {
                "summary": "Ensure that the most important facts are present in the static HTML and do not require JS rendering.",
                "priority": "medium"
            }
        })
        
    # CR-005
    noscripts = soup.find_all("noscript")
    has_meaningful_noscript = False
    for ns in noscripts:
        ns_text = ns.get_text(separator=' ', strip=True)
        if len(ns_text.split()) > 10:
            has_meaningful_noscript = True
            break
            
    if not has_meaningful_noscript:
        findings.append({
            "id": "CR-005",
            "title": "No Noscript Fallback",
            "severity": "medium",
            "evidence": f"0 <noscript> tags with meaningful fallback content. Non-JavaScript crawlers receive no alternative content.",
            "suggested_action": {
                "summary": "Provide a <noscript> fallback containing the core content for crawlers that do not execute JavaScript.",
                "priority": "medium"
            }
        })
        
    # Phase C — Facts Locked in Non-Text
    
    # CR-007
    images = soup.find_all("img")
    content_images = [img for img in images if img.get("role") != "presentation" and img.get("alt") != ""]
    missing_or_trivial = 0
    for img in content_images:
        alt = img.get("alt")
        if not alt:
            missing_or_trivial += 1
        else:
            alt_words = alt.strip().split()
            if len(alt_words) < 5:
                missing_or_trivial += 1
                
    if content_images and (missing_or_trivial / len(content_images)) > 0.5:
        findings.append({
            "id": "CR-007",
            "title": "Facts Locked in Images",
            "severity": "high",
            "evidence": f"{missing_or_trivial}/{len(content_images)} content images have missing or trivial alt text (<5 words) — facts within these images are invisible to AI text extraction.",
            "suggested_action": {
                "summary": "Add descriptive alt text to all non-decorative images to ensure AI models can understand the visual facts.",
                "priority": "high"
            }
        })
        
    # CR-008
    iframes = soup.find_all("iframe")
    video_iframes = [ifr for ifr in iframes if ifr.get("src") and re.search(r'youtube|vimeo|wistia|loom', ifr.get("src"), re.I)]
    
    videos_without_track = [v for v in soup.find_all("video") if not v.find("track")]
    canvases = soup.find_all("canvas")
    
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    has_video_object = False
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "VideoObject":
                has_video_object = True
                break
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "VideoObject":
                        has_video_object = True
                        break
        except Exception:
            pass
            
    unsupported_media = (len(video_iframes) > 0 and not has_video_object) or len(videos_without_track) > 0 or len(canvases) > 0
    
    if unsupported_media:
        iframe_count = len(video_iframes)
        video_count = len(videos_without_track)
        findings.append({
            "id": "CR-008",
            "title": "Media Embeds Without Text Alternatives",
            "severity": "medium",
            "evidence": f"{iframe_count} video iframes and {video_count} video elements found without Schema VideoObject markup or on-page text transcripts.",
            "suggested_action": {
                "summary": "Provide VideoObject schema markup or explicit text transcripts on the page for video and canvas content.",
                "priority": "medium"
            }
        })
        
    return findings

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_crawl_render.py <url>")
        sys.exit(1)
        
    url = sys.argv[1]
    
    try:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Setup robots.txt parser
        robots_url = urljoin(base_url, '/robots.txt')
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            rp = None
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        findings = analyze_crawl_render(soup, rp, response.headers, url, base_url)
        print(json.dumps(findings, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
