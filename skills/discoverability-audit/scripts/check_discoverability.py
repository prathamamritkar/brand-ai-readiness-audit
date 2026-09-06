import json
import re
import sys
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def analyze_discoverability(soup, url, base_url=""):
    findings = []
    
    # Pre-parse JSON-LD scripts
    scripts = soup.find_all('script', type='application/ld+json')
    
    # Phase A — Structured Data Presence
    
    # DISC-001
    if not scripts:
        findings.append({
            "id": "DISC-001",
            "title": "No Schema.org Structured Data",
            "severity": "high",
            "evidence": "0 JSON-LD blocks found in the DOM. AI systems have no structured entity data to map.",
            "suggested_action": {
                "summary": "Implement Schema.org JSON-LD to provide explicit entity context to AI systems.",
                "priority": "high"
            }
        })
        
    valid_jsonld_blocks = []
    failed_jsonld_blocks = 0
    
    for script in scripts:
        try:
            content = script.string if script.string else ""
            data = json.loads(content)
            valid_jsonld_blocks.append(data)
        except (json.JSONDecodeError, TypeError):
            failed_jsonld_blocks += 1

    # DISC-002
    if failed_jsonld_blocks > 0:
        findings.append({
            "id": "DISC-002",
            "title": "JSON-LD Syntax Errors",
            "severity": "high",
            "evidence": f"{failed_jsonld_blocks}/{len(scripts)} JSON-LD blocks contain invalid JSON syntax that silently fails in AI parsers.",
            "suggested_action": {
                "summary": "Fix JSON syntax errors so AI crawlers can successfully parse the structured data.",
                "priority": "high"
            }
        })
        
    # Process items
    items = []
    for data in valid_jsonld_blocks:
        if isinstance(data, dict):
            items.extend(data.get('@graph', [data]))
        elif isinstance(data, list):
            items.extend(data)
            
    # Helper to extract all types
    extracted_types = set()
    for item in items:
        if isinstance(item, dict):
            t = item.get('@type')
            if isinstance(t, str):
                extracted_types.add(t)
            elif isinstance(t, list):
                extracted_types.update(t)

    generic_types = {"WebSite", "WebPage", "SearchAction"}
    domain_specific_types = {"Organization", "Product", "Service", "FAQPage", "HowTo", "LocalBusiness", "Article", "BreadcrumbList", "Person", "Event", "Course", "SoftwareApplication"}
    
    # DISC-003
    if valid_jsonld_blocks and extracted_types:
        has_domain_specific = any(t in domain_specific_types for t in extracted_types)
        has_generic = any(t in generic_types for t in extracted_types)
        if not has_domain_specific and has_generic:
            findings.append({
                "id": "DISC-003",
                "title": "Shallow Schema Type Coverage",
                "severity": "medium",
                "evidence": f"JSON-LD contains only generic types {list(extracted_types)}. No domain-specific entity types found.",
                "suggested_action": {
                    "summary": "Implement domain-specific schemas (e.g., Organization, Product) to ground AI knowledge graphs.",
                    "priority": "medium"
                }
            })

    # Phase B — Entity Disambiguation
    target_entities = {"Organization", "LocalBusiness", "Person", "Corporation", "Brand"}
    
    for item in items:
        if not isinstance(item, dict):
            continue
            
        t = item.get('@type')
        item_types = [t] if isinstance(t, str) else t if isinstance(t, list) else []
        
        is_target = any(tt in target_entities for tt in item_types)
        if is_target:
            name = item.get('name', 'Unnamed Entity')
            
            # DISC-004
            same_as = item.get('sameAs')
            if not same_as:
                findings.append({
                    "id": "DISC-004",
                    "title": "Entity Ambiguity — No sameAs Links",
                    "severity": "high",
                    "evidence": f"Entity '{name}' found in JSON-LD but contains 0 'sameAs' links. AI cannot disambiguate this brand from entities with the same name.",
                    "suggested_action": {
                        "summary": "Add authoritative sameAs links (e.g., Wikipedia, LinkedIn, Wikidata) to establish unique brand identity.",
                        "priority": "high"
                    }
                })
            
            # DISC-005
            if '@id' not in item:
                findings.append({
                    "id": "DISC-005",
                    "title": "No Stable Entity Anchor (@id)",
                    "severity": "medium",
                    "evidence": f"Entity '{name}' lacks '@id' URI. Without a stable identifier, cross-page entity resolution fails — each page creates a disconnected identity.",
                    "suggested_action": {
                        "summary": "Provide stable @id URIs for entities to allow AI to connect information across pages.",
                        "priority": "medium"
                    }
                })

    # DISC-006
    canonical = soup.find('link', rel='canonical')
    if not canonical:
        findings.append({
            "id": "DISC-006",
            "title": "Missing Canonical URL",
            "severity": "high",
            "evidence": "No <link rel='canonical'> found. Content attribution may leak across URL variants, confusing AI crawlers about the authoritative source.",
            "suggested_action": {
                "summary": "Implement a canonical link tag to ensure all AI credit and signals consolidate to the primary URL.",
                "priority": "high"
            }
        })
        
    # Phase C — SEO Hygiene & Social Signals
    
    # DISC-007
    title_tag = soup.find('title')
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    missing_elements = []
    
    if not title_tag or not title_tag.string or not title_tag.string.strip():
        missing_elements.append("<title>")
    if not meta_desc or not meta_desc.get('content') or not meta_desc.get('content').strip():
        missing_elements.append("<meta name='description'>")
        
    if missing_elements:
        findings.append({
            "id": "DISC-007",
            "title": "Missing Title or Meta Description",
            "severity": "medium",
            "evidence": f"Page is missing {', '.join(missing_elements)}. These are primary signals AI assistants use for page summarization.",
            "suggested_action": {
                "summary": "Add robust title and meta description tags to guide AI page summarization and semantic relevance.",
                "priority": "medium"
            }
        })
        
    # DISC-008
    og_tags = ['og:title', 'og:description', 'og:type', 'og:image']
    missing_og = []
    
    for og in og_tags:
        if not soup.find('meta', attrs={'property': og}):
            missing_og.append(og)
            
    if missing_og:
        findings.append({
            "id": "DISC-008",
            "title": "Missing Open Graph Markup",
            "severity": "medium",
            "evidence": f"{len(missing_og)}/4 core Open Graph tags missing ({', '.join(missing_og)}). AI agents and social platforms use these as summary signals.",
            "suggested_action": {
                "summary": "Include Open Graph tags as strong semantic signals for AI parsing and content extraction.",
                "priority": "medium"
            }
        })
        
    # DISC-009: Only flag hreflang if there are multi-language signals on the page,
    # otherwise it fires on every single-language site and becomes noise.
    hreflang = soup.find('link', attrs={'rel': 'alternate', 'hreflang': True})
    if not hreflang:
        # Check for genuine multi-language signals before proactively recommending
        lang_signals = (
            soup.find('select', attrs={'name': re.compile(r'lang|language|locale|region', re.I)}) or
            soup.find('a', href=re.compile(r'/[a-z]{2}(-[a-z]{2})?/', re.I)) or
            soup.find(attrs={'data-lang': True}) or
            soup.find(attrs={'hreflang': True})
        )
        if lang_signals:
            findings.append({
                "id": "DISC-009",
                "title": "[Proactive] Hreflang Not Declared",
                "severity": "medium",
                "evidence": "Multi-language signals detected on the page (language selector or locale-prefixed links) but no <link rel='alternate' hreflang='...'> tags declared. AI may misattribute content language.",
                "suggested_action": {
                    "summary": "Declare hreflang alternate links for each language/region variant. This ensures AI models correctly contextualize content by language and do not mix up regional versions.",
                    "priority": "medium"
                }
            })
        
    # DISC-010
    has_breadcrumb = 'BreadcrumbList' in extracted_types
    if not has_breadcrumb:
        findings.append({
            "id": "DISC-010",
            "title": "[Proactive] BreadcrumbList Schema Missing",
            "severity": "medium",
            "evidence": "No BreadcrumbList structured data found. Adding breadcrumb schema helps AI understand site hierarchy and improves navigation context.",
            "suggested_action": {
                "summary": "Implement BreadcrumbList schema to map out site architecture explicitly for AI understanding.",
                "priority": "medium"
            }
        })
        
    return findings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Analyze a URL for AI Discoverability readiness")
    parser.add_argument("url", help="The URL to analyze")
    args = parser.parse_args()
    
    try:
        response = requests.get(args.url, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        parsed_url = urlparse(args.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        results = analyze_discoverability(soup, args.url, base_url)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "message": "Failed to fetch or parse the URL."
        }, indent=2))
        sys.exit(1)