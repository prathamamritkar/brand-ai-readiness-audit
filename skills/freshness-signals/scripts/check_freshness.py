import sys
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

def analyze_freshness(soup, response_headers=None, url='', robots_txt_raw=''):
    """
    Analyzes a webpage for AI-readiness freshness signals.
    """
    if response_headers is None:
        response_headers = {}
    
    findings = []
    current_year = datetime.now().year

    def parse_date(date_str):
        if not date_str:
            return None
        formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y']
        for fmt in formats:
            try:
                s = date_str.split('T')[0] if fmt == '%Y-%m-%d' else date_str
                if fmt == '%Y':
                    s = date_str[:4]
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
            
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                pass
        return None

    json_ld_data = []
    schemas = soup.find_all('script', type='application/ld+json')
    for schema in schemas:
        try:
            if schema.string:
                data = json.loads(schema.string)
                items = data.get('@graph', [data]) if isinstance(data, dict) else data if isinstance(data, list) else [data]
                json_ld_data.extend(items)
        except Exception:
            pass

    # ==========================================
    # Phase A — Temporal Markers
    # ==========================================

    # FR-001: No Machine-Readable Date Markup
    has_date = False
    
    for item in json_ld_data:
        if isinstance(item, dict) and ('datePublished' in item or 'dateModified' in item):
            has_date = True
            break
            
    if not has_date and soup.find('time', attrs={'datetime': True}):
        has_date = True
        
    if not has_date:
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            prop = meta.get('property', '').lower()
            if 'date' in name or 'modified' in name or 'date' in prop or 'modified' in prop:
                has_date = True
                break
                
    if not has_date:
        last_modified = next((v for k, v in response_headers.items() if k.lower() == 'last-modified'), None)
        if last_modified:
            has_date = True

    if not has_date:
        findings.append({
            "id": "FR-001",
            "title": "No Machine-Readable Date Markup",
            "severity": "high",
            "evidence": "No machine-readable date found in JSON-LD, <time> tags, date meta tags, or HTTP Last-Modified header. AI systems cannot assess content freshness.",
            "suggested_action": {
                "summary": "Provide explicit, machine-readable date signals (e.g., dateModified in JSON-LD) so AI models can correctly timestamp the information and trust its recency.",
                "priority": "high"
            }
        })

    # FR-002: Stale Copyright Year
    footer = soup.find('footer')
    text_to_search = footer.get_text() if footer else soup.get_text()
    copyright_regex = r'(?:©|&copy;|copyright|\(c\))\s*(?:\d{4}\s*[-–—]\s*)?(\d{4})'
    copyright_matches = re.findall(copyright_regex, text_to_search, re.IGNORECASE)
    footer_year = None
    
    if copyright_matches:
        try:
            years = [int(y) for y in copyright_matches]
            latest_year = max(years)
            footer_year = latest_year
            if current_year - latest_year > 1:
                findings.append({
                    "id": "FR-002",
                    "title": "Stale Copyright Year",
                    "severity": "medium",
                    "evidence": f"Copyright year {latest_year} detected (current year: {current_year}). Stale temporal signals decrease AI citation confidence.",
                    "suggested_action": {
                        "summary": "Update copyright years to the current year dynamically. AI systems use this as a basic proxy for general site maintenance and content freshness.",
                        "priority": "medium"
                    }
                })
        except ValueError:
            pass

    # FR-003: Outdated Schema Dates
    # FR-004: Temporal Contradiction
    schema_dates = []
    for item in json_ld_data:
        if isinstance(item, dict):
            for field in ['datePublished', 'dateModified']:
                if field in item:
                    parsed = parse_date(item[field])
                    if parsed:
                        schema_dates.append((field, parsed, item[field]))
                        age_years = current_year - parsed.year
                        if age_years > 2:
                            findings.append({
                                "id": "FR-003",
                                "title": "Outdated Schema Dates",
                                "severity": "high",
                                "evidence": f"Schema {field} is '{item[field]}', over {age_years} years stale. AI systems with recency bias will deprioritize this content.",
                                "suggested_action": {
                                    "summary": "Update schema dates for refreshed content. Stale timestamps signal deprecated information to AI answering models.",
                                    "priority": "high"
                                }
                            })

    all_parsed_years = []
    if footer_year:
        all_parsed_years.append(footer_year)
    for _, parsed, _ in schema_dates:
        all_parsed_years.append(parsed.year)
    
    time_tags = soup.find_all('time', attrs={'datetime': True})
    for t in time_tags:
        parsed = parse_date(t.get('datetime'))
        if parsed:
            all_parsed_years.append(parsed.year)

    if all_parsed_years:
        min_year = min(all_parsed_years)
        max_year = max(all_parsed_years)
        if max_year - min_year > 2:
            # Build dynamic evidence based on what sources exist
            sources = []
            if schema_dates:
                sources.append(f"JSON-LD {schema_dates[0][0]} '{schema_dates[0][2]}'")
            if footer_year:
                sources.append(f"footer copyright '© {footer_year}'")
            time_tag_years = [y for _, p, _ in [] for y in []]  # placeholder
            # Just use a generic description
            evidence_str = f"Temporal contradiction detected: date sources span {min_year}–{max_year} (>{max_year - min_year} year gap). "
            if sources:
                evidence_str += f"Sources: {', '.join(sources)}. "
            evidence_str += "Conflicting timestamps reduce AI trust in content accuracy."
            findings.append({
                "id": "FR-004",
                "title": "Temporal Contradiction",
                "severity": "high",
                "evidence": evidence_str,
                "suggested_action": {
                    "summary": "Synchronize dates across visible footer, schema, and HTML tags to present a unified temporal signal to AI crawlers.",
                    "priority": "high"
                }
            })

    # ==========================================
    # Phase B — Corroboration Signals
    # ==========================================

    # FR-005: No Author or Publisher Attribution
    has_attribution = False
    for item in json_ld_data:
        if isinstance(item, dict) and ('author' in item or 'publisher' in item):
            has_attribution = True
            break
    if not has_attribution:
        if soup.find('meta', attrs={'name': lambda x: x and x.lower() == 'author'}):
            has_attribution = True

    if not has_attribution:
        findings.append({
            "id": "FR-005",
            "title": "No Author or Publisher Attribution",
            "severity": "medium",
            "evidence": "No author or publisher attribution found in structured data or meta tags. Unattributed content is harder for AI to trust and cite as an authoritative source.",
            "suggested_action": {
                "summary": "Add explicit author or publisher properties to JSON-LD. AI systems require entity attribution to verify expertise and establish source credibility.",
                "priority": "medium"
            }
        })

    # FR-006: [Proactive] No FAQ or HowTo Schema
    has_faq_howto = False
    for item in json_ld_data:
        if isinstance(item, dict):
            types = item.get('@type', '')
            if isinstance(types, str):
                types = [types]
            if any(t in ['FAQPage', 'HowTo'] for t in types):
                has_faq_howto = True
                break
                
    if not has_faq_howto:
        findings.append({
            "id": "FR-006",
            "title": "[Proactive] No FAQ or HowTo Schema",
            "severity": "medium",
            "evidence": "No FAQPage or HowTo structured data found. Research shows these are among the highest-citation schema types in AI overviews — adding them proactively increases citation probability.",
            "suggested_action": {
                "summary": "Implement FAQPage or HowTo structured data if applicable. These formats are heavily favored by LLMs for generative search answers.",
                "priority": "medium"
            }
        })

    # FR-007: [Proactive] Sitemap Not Declared in robots.txt
    if robots_txt_raw:
        has_sitemap = any(line.lower().startswith('sitemap:') for line in robots_txt_raw.splitlines())
        if not has_sitemap:
            findings.append({
                "id": "FR-007",
                "title": "[Proactive] Sitemap Not Declared in robots.txt",
                "severity": "medium",
                "evidence": "No Sitemap directive found in robots.txt. AI crawlers use sitemaps to discover content and prioritize recently updated pages.",
                "suggested_action": {
                    "summary": "Add a Sitemap directive to robots.txt to ensure AI indexing bots can rapidly discover refreshed content.",
                    "priority": "medium"
                }
            })
    else:
        # No robots.txt at all — sitemap is definitely not declared
        findings.append({
            "id": "FR-007",
            "title": "[Proactive] Sitemap Not Declared in robots.txt",
            "severity": "medium",
            "evidence": "No robots.txt file found on the server. Without a robots.txt, AI crawlers have no Sitemap directive to guide content discovery and freshness prioritization.",
            "suggested_action": {
                "summary": "Create a robots.txt file with a Sitemap directive pointing to your XML sitemap to help AI crawlers discover and prioritize recently updated content.",
                "priority": "medium"
            }
        })

    return findings

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_freshness.py <url>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    
    try:
        response = requests.get(target_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        parsed = urlparse(target_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        robots_txt_raw = ''
        try:
            robots_response = requests.get(robots_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if robots_response.status_code == 200:
                robots_txt_raw = robots_response.text
        except Exception:
            pass
            
        results = analyze_freshness(soup, dict(response.headers), target_url, robots_txt_raw)
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(json.dumps([{
            "id": "FR-ERROR",
            "title": "Fetch Error",
            "severity": "critical",
            "evidence": str(e),
            "suggested_action": {
                "summary": "Fix connection issue",
                "priority": "critical"
            }
        }], indent=2))
