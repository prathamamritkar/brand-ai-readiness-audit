import sys
import re
import json
import urllib.robotparser
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

def _get_visible_text(soup):
    # Deep copy via re-parse — copy.copy() is a SHALLOW copy and shares
    # child nodes with the original, causing decompose() to mutate it.
    soup_copy = BeautifulSoup(str(soup), "html.parser")
    for tag in soup_copy(["script", "style", "noscript", "svg", "head", "title", "meta"]):
        tag.decompose()
    return soup_copy.get_text(separator=' ', strip=True)


def _is_bot_blocked(response_headers, soup, status_code):
    """
    Detect if the response is a bot-block, CAPTCHA, or redirect wall
    rather than real content. Prevents false-positive JS-render findings.
    """
    # Check HTTP status: 403, 429, 503 typically indicate access denial
    if status_code in (403, 429, 503):
        return True
    # Check for CAPTCHA indicators in title or body
    title_tag = soup.find("title")
    title_text = (title_tag.get_text(strip=True) if title_tag else "").lower()
    captcha_signals = ["captcha", "access denied", "blocked", "robot check",
                       "are you human", "ddos", "cloudflare", "just a moment"]
    if any(s in title_text for s in captcha_signals):
        return True
    # Very small HTML body with no meaningful structure often = bot block
    body = soup.find("body")
    body_text = body.get_text(strip=True) if body else ""
    if len(body_text) < 50 and status_code not in (200, 201):
        return True
    return False

def analyze_crawl_render(soup, robots_parser, response_headers, url, base_url, status_code=200):
    findings = []

    # Phase A — Crawl Access

    # Guard: if the site is bot-blocking, skip JS-render checks to avoid false positives
    bot_blocked = _is_bot_blocked(response_headers, soup, status_code)

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
    # Skip these checks if the site is bot-blocking — a CAPTCHA page has 0 words
    # but that's access denial, not JS rendering. Reporting CR-003 there = false positive.
    if bot_blocked:
        findings.append({
            "id": "CR-003",
            "title": "Site Returned Bot-Block / CAPTCHA Response",
            "severity": "high",
            "evidence": f"The site appears to be blocking automated requests (HTTP {status_code} or CAPTCHA page detected). Content analysis is unreliable — AI crawlers may be similarly blocked.",
            "suggested_action": {
                "summary": "Verify the site allows non-browser HTTP clients. Bot-blocking affects AI crawlers as well as audit tools. Consider configuring Cloudflare or WAF rules to permit known AI crawlers.",
                "priority": "high"
            }
        })
    else:
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
                "evidence": f"Found SSR markers in HTML: {', '.join(detected_markers)}. Content is likely pre-rendered server-side and extractable by AI crawlers.",
                "suggested_action": {
                    "summary": "Good signal — verify critical content (pricing, specs, FAQs) is included in the server-rendered payload and not deferred to client-side hydration.",
                    "priority": "medium"
                }
            })

        if word_count < 100:
            evidence = f"Raw HTML contains only {word_count} readable words — core facts entirely dependent on client-side JavaScript execution."
            if not ssr_detected:
                evidence += " No SSR framework markers detected."
            findings.append({
                "id": "CR-003",
                "title": "Severe JS Rendering Dependency",
                "severity": "high",
                "evidence": evidence,
                "suggested_action": {
                    "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so core facts exist in the static HTML payload and are extractable by AI crawlers without JavaScript execution.",
                    "priority": "high"
                }
            })
        elif 100 <= word_count <= 300 and script_count > 5:
            evidence = f"{word_count} words in static HTML with {script_count} external scripts — partial SSR but heavy JS dependency risk."
            if not ssr_detected:
                evidence += " No SSR framework markers detected."
            findings.append({
                "id": "CR-004",
                "title": "Moderate JS Content Risk",
                "severity": "medium",
                "evidence": evidence,
                "suggested_action": {
                    "summary": "Ensure key facts (pricing, features, contact info) are present in the server-rendered HTML and do not require JS execution to appear.",
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

    # CR-007: Images with missing or meaningless alt text
    # Excludes: role="presentation" (decorative), alt="" (explicit decorative marker)
    # Flags: missing alt OR alt that is a generic placeholder word
    _TRIVIAL_ALTS = {"image", "img", "photo", "picture", "screenshot",
                     "chart", "graph", "banner", "thumbnail", "icon",
                     "placeholder", "figure", "pic", "graphic"}
    images = soup.find_all("img")
    # Exclude explicitly decorative images (alt="" or role="presentation")
    content_images = [
        img for img in images
        if img.get("role") != "presentation" and img.get("alt") is not None
    ]
    missing_or_trivial = 0
    for img in content_images:
        alt = (img.get("alt") or "").strip()
        if not alt:
            # alt="" is decorative — skip. alt attribute completely absent = missing
            if img.get("alt") is None:
                missing_or_trivial += 1
        else:
            # Flag if alt is a single generic placeholder word
            alt_lower = alt.lower()
            if alt_lower in _TRIVIAL_ALTS:
                missing_or_trivial += 1
            # Flag if alt is a single-word non-descriptive token under 3 chars
            elif len(alt.split()) == 1 and len(alt) <= 2:
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
