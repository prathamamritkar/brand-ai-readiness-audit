import sys
import json
import re
from bs4 import BeautifulSoup
import requests

def analyze_engagement(soup: BeautifulSoup, url: str) -> list:
    findings = []
    
    # Phase A: Structural Orientation
    # ENG-001 & ENG-002
    h1_tags = soup.find_all('h1')
    if len(h1_tags) == 0:
        findings.append({
            "id": "ENG-001",
            "title": "Missing Primary <h1>",
            "severity": "high",
            "evidence": "0 <h1> tags found in the DOM. The page lacks a definitive structural title, causing weak orientation for both visitors and AI systems.",
            "suggested_action": {
                "summary": "Add a single descriptive <h1> tag to serve as the structural anchor for semantic processing.",
                "priority": "high"
            }
        })
    elif len(h1_tags) > 1:
        texts = [h.get_text(strip=True)[:60] for h in h1_tags]
        findings.append({
            "id": "ENG-002",
            "title": "Conflicting <h1> Hierarchy",
            "severity": "medium",
            "evidence": f"Found {len(h1_tags)} <h1> tags: {texts}. Multiple primary headings fracture the semantic context.",
            "suggested_action": {
                "summary": "Consolidate to a single <h1> and demote others to <h2> to maintain a clear topic hierarchy for AI extraction.",
                "priority": "medium"
            }
        })

    # ENG-003
    heading_pattern = re.compile(r'^h[1-6]$', re.IGNORECASE)
    all_headings = soup.find_all(heading_pattern)
    gaps = []
    prev_level = None
    for h in all_headings:
        level = int(h.name[1])
        if prev_level is not None:
            if level > prev_level + 1:
                gaps.append(f"h{prev_level}->h{level}")
        prev_level = level
    
    if gaps:
        findings.append({
            "id": "ENG-003",
            "title": "Heading Level Gaps",
            "severity": "medium",
            "evidence": f"Heading hierarchy has {len(gaps)} level gap(s): {', '.join(gaps)}. Example: <h{prev_level}> followed by <h{level}> skipping levels. Broken hierarchy degrades semantic outline for AI and screen readers.",
            "suggested_action": {
                "summary": "Ensure heading levels nest sequentially without skipping levels to provide a robust document outline.",
                "priority": "medium"
            }
        })

    # ENG-004
    landmarks = ['main', 'nav', 'header', 'footer', 'article', 'section']
    found_landmarks = [tag for tag in landmarks if soup.find(tag)]
    if not found_landmarks:
        findings.append({
            "id": "ENG-004",
            "title": "No Semantic Landmarks",
            "severity": "high",
            "evidence": "0 semantic landmark elements found (no <main>, <nav>, <header>, <footer>, <article>, or <section>). Page is a flat div-based layout with no navigational context for AI or assistive technology.",
            "suggested_action": {
                "summary": "Replace generic <div> wrappers with semantic landmark tags to establish logical regions for machine parsing.",
                "priority": "high"
            }
        })

    # Phase B: Context Retention
    # ENG-005
    if h1_tags:
        first_h1 = h1_tags[0]
        next_p = first_h1.find_next('p')
        if next_p:
            p_text = next_p.get_text(strip=True)
            word_count = len(p_text.split())
            if word_count > 0:
                if word_count < 20:
                    findings.append({
                        "id": "ENG-005",
                        "title": "Weak Lead Answer Density",
                        "severity": "medium",
                        "evidence": f"Lead paragraph after <h1> contains only {word_count} words. The page fails to front-load its value proposition — AI citations draw from the first 30% of content.",
                        "suggested_action": {
                            "summary": "Expand the lead paragraph to concisely answer the query directly, enabling immediate context capture.",
                            "priority": "medium"
                        }
                    })
                elif word_count > 120:
                    findings.append({
                        "id": "ENG-005",
                        "title": "Weak Lead Answer Density",
                        "severity": "medium",
                        "evidence": f"Lead paragraph after <h1> contains {word_count} words. Overly dense lead text overwhelms visitors and reduces scannability.",
                        "suggested_action": {
                            "summary": "Break down the overly long lead paragraph to ensure better parsing and readability.",
                            "priority": "medium"
                        }
                    })

    # ENG-006
    paragraphs = soup.find_all('p')
    dense_ps = []
    for p in paragraphs:
        p_text = p.get_text(strip=True)
        count = len(p_text.split())
        if count > 150:
            dense_ps.append(count)
    if len(dense_ps) > 2:
        avg = sum(dense_ps) / len(dense_ps)
        findings.append({
            "id": "ENG-006",
            "title": "Wall-of-Text Paragraphs",
            "severity": "medium",
            "evidence": f"{len(dense_ps)} paragraph(s) exceed 150 words (average: {avg:.1f} words). Dense text blocks cause scanning fatigue and visitor bounce.",
            "suggested_action": {
                "summary": "Split long paragraphs into shorter segments of 2-3 sentences to improve pacing and maintain attention.",
                "priority": "medium"
            }
        })

    # ENG-007
    soup_copy = BeautifulSoup(str(soup), 'html.parser')
    for script_or_style in soup_copy(["script", "style"]):
        script_or_style.decompose()
    visible_text = soup_copy.get_text(separator=' ')
    total_words = len(visible_text.split())
    
    if total_words > 600:
        breakers = soup.find_all(['ul', 'ol', 'table', 'blockquote', 'h2', 'h3', 'h4'])
        if len(breakers) < 3:
            counts = {b.name: 0 for b in breakers}
            for b in breakers: 
                counts[b.name] += 1
            detail = ", ".join(f"{k}: {v}" for k, v in counts.items() if v > 0)
            if not detail:
                detail = "none found"
            findings.append({
                "id": "ENG-007",
                "title": "Low Scannability — Missing Structural Breakers",
                "severity": "medium",
                "evidence": f"Page has {total_words} words but only {len(breakers)} structural breakers ({detail}). Low visual anchor density forces continuous reading and triggers user bounce.",
                "suggested_action": {
                    "summary": "Introduce lists, blockquotes, or subheadings to chunk long content into accessible formats.",
                    "priority": "medium"
                }
            })

    # ENG-008
    html_tag = soup.find('html')
    if html_tag and not html_tag.has_attr('lang'):
        findings.append({
            "id": "ENG-008",
            "title": "No Language Declaration",
            "severity": "medium",
            "evidence": "<html> tag has no 'lang' attribute. Screen readers and AI systems cannot determine the content language, leading to potential misinterpretation.",
            "suggested_action": {
                "summary": "Add a valid lang attribute to the <html> element specifying the document's primary language.",
                "priority": "medium"
            }
        })

    # Phase C: Accessible Context
    # ENG-009
    interactive_elements = soup.find_all(['button', 'a'])
    unlabeled_count = 0
    for el in interactive_elements:
        if el.name == 'a' and el.get('href', '').startswith('#') and el.get_text(strip=True):
            continue
        text = el.get_text(strip=True)
        aria_label = el.get('aria-label', '').strip()
        title = el.get('title', '').strip()
        if not text and not aria_label and not title:
            unlabeled_count += 1
    
    if unlabeled_count > 3:
        findings.append({
            "id": "ENG-009",
            "title": "Unlabeled Interactive Elements",
            "severity": "high",
            "evidence": f"{unlabeled_count} interactive elements (<button>, <a>) have no visible text, aria-label, or title attribute. These are completely inaccessible and provide zero context for AI extraction.",
            "suggested_action": {
                "summary": "Provide descriptive text or aria-labels for all interactive elements to ensure accessibility and machine interpretability.",
                "priority": "high"
            }
        })

    # ENG-010
    meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
    if not meta_viewport:
        findings.append({
            "id": "ENG-010",
            "title": "[Proactive] Missing Viewport Meta",
            "severity": "medium",
            "evidence": "No <meta name='viewport'> tag found. Mobile visitors receive an unoptimized desktop layout, causing high bounce rates on mobile devices.",
            "suggested_action": {
                "summary": "Add a viewport meta tag to enable responsive layouts and improve retention on mobile.",
                "priority": "medium"
            }
        })

    return findings

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python check_engagement.py <url>"}))
        sys.exit(1)
    
    url = sys.argv[1]
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        results = analyze_engagement(soup, url)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(json.dumps([{"error": str(e)}], indent=2))
        sys.exit(1)