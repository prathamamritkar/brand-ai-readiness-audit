import sys
import json
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

def analyze_social_authority(soup, url, base_url):
    """
    Analyzes a webpage for social proof and authority signals.
    """
    findings = []
    
    # Extract JSON-LD scripts
    json_lds = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            if script.string:
                data = json.loads(script.string)
                if isinstance(data, list):
                    json_lds.extend(data)
                else:
                    json_lds.append(data)
        except json.JSONDecodeError:
            continue

    def check_schema_types(data, target_types):
        if isinstance(data, dict):
            type_val = data.get('@type', '')
            if isinstance(type_val, str) and type_val in target_types:
                return True
            if isinstance(type_val, list) and any(t in target_types for t in type_val):
                return True
            for val in data.values():
                if check_schema_types(val, target_types):
                    return True
        elif isinstance(data, list):
            for item in data:
                if check_schema_types(item, target_types):
                    return True
        return False

    # SA-001: No Review/Rating Schema (high)
    has_review_schema = False
    for ld in json_lds:
        if check_schema_types(ld, ['AggregateRating', 'Review', 'Rating']):
            has_review_schema = True
            break
            
    if not has_review_schema:
        # Also check DOM heuristically
        if not soup.find(itemprop=re.compile('(?i)rating|review')):
            findings.append({
                "id": "SA-001",
                "title": "No Review/Rating Schema",
                "severity": "high",
                "evidence": "No review or rating structured data found. AI systems prioritize sources with verified social proof.",
                "suggested_action": {
                    "summary": "Add AggregateRating or Review schema markup to legitimate reviews on the site.",
                    "priority": "high"
                }
            })

    # SA-002: No Social Media Profile Links (high)
    social_domains = ['twitter.com', 'x.com', 'facebook.com', 'linkedin.com', 'instagram.com', 'youtube.com', 'github.com', 'tiktok.com']
    has_social_link = False
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if any(domain in href for domain in social_domains):
            has_social_link = True
            break
            
    if not has_social_link:
        findings.append({
            "id": "SA-002",
            "title": "No Social Media Profile Links",
            "severity": "high",
            "evidence": "No social media profile links detected. Social presence corroborates brand identity for AI disambiguation.",
            "suggested_action": {
                "summary": "Link to verified social media profiles from the website (typically in footer or contact page).",
                "priority": "high"
            }
        })

    # SA-003: No Contact Information Visible (medium)
    has_contact = False
    if soup.find('a', href=re.compile(r'^mailto:')) or soup.find('a', href=re.compile(r'^tel:')) or soup.find('address'):
        has_contact = True
    else:
        for ld in json_lds:
            if check_schema_types(ld, ['ContactPoint', 'PostalAddress']):
                has_contact = True
                break
                
    if not has_contact:
        findings.append({
            "id": "SA-003",
            "title": "No Contact Information Visible",
            "severity": "medium",
            "evidence": "No contact information found. Visible contact details signal a legitimate, reachable business.",
            "suggested_action": {
                "summary": "Ensure email, phone number, or physical address are present on the page and properly marked up.",
                "priority": "medium"
            }
        })

    # SA-004: No Testimonial or Case Study Signals (medium)
    testimonial_classes = ['testimonial', 'review', 'case-study', 'client', 'customer-story']
    has_testimonial = False
    
    for tag in soup.find_all(class_=True):
        classes = tag.get('class', [])
        if any(any(tc in cls.lower() for tc in testimonial_classes) for cls in classes):
            has_testimonial = True
            break
            
    if not has_testimonial:
        for tag in soup.find_all(id=True):
            if any(tc in tag.get('id', '').lower() for tc in testimonial_classes):
                has_testimonial = True
                break
                
    if not has_testimonial:
        if soup.find('blockquote', cite=True):
            has_testimonial = True
            
    if not has_testimonial:
        findings.append({
            "id": "SA-004",
            "title": "No Testimonial or Case Study Signals",
            "severity": "medium",
            "evidence": "No testimonial or case study content detected.",
            "suggested_action": {
                "summary": "Incorporate testimonials, case studies, or customer stories with clear class names (e.g., 'testimonial').",
                "priority": "medium"
            }
        })

    # SA-005: No About Page Linked (medium)
    about_paths = ['/about', '/about-us', '/who-we-are', '/our-story', '/team', '/company']
    has_about_link = False
    
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if any(path in href for path in about_paths) or 'about' in a.get_text().lower():
            has_about_link = True
            break
            
    if not has_about_link:
        findings.append({
            "id": "SA-005",
            "title": "No About Page Linked",
            "severity": "medium",
            "evidence": "No about/team page linked. Brand narrative pages help AI build entity context.",
            "suggested_action": {
                "summary": "Include a link to an 'About' or 'Company' page in the main navigation or footer.",
                "priority": "medium"
            }
        })

    # SA-006: Missing ContactPoint or LocalBusiness Schema (medium)
    has_org_brand = False
    has_contact_schema = False
    
    for ld in json_lds:
        if check_schema_types(ld, ['Organization', 'Brand', 'Corporation']):
            has_org_brand = True
        if check_schema_types(ld, ['ContactPoint', 'LocalBusiness', 'PostalAddress']):
            has_contact_schema = True
            
    if has_org_brand and not has_contact_schema:
        findings.append({
            "id": "SA-006",
            "title": "Missing ContactPoint or LocalBusiness Schema",
            "severity": "medium",
            "evidence": "Organization schema found but no ContactPoint or address data.",
            "suggested_action": {
                "summary": "Enrich Organization schema with ContactPoint or PostalAddress to provide robust context.",
                "priority": "medium"
            }
        })

    # SA-007: [Proactive] No Press/Media or Awards Section (medium)
    press_terms = ['press', 'media', 'news', 'awards', 'recognition', 'featured-in', 'as-seen', 'featured in', 'as seen']
    has_press = False
    
    # Check links and class names
    for a in soup.find_all('a', href=True):
        text = a.get_text().lower()
        href = a['href'].lower()
        if any(term in text or term in href for term in press_terms):
            has_press = True
            break
            
    if not has_press:
        for tag in soup.find_all(class_=True):
            classes = tag.get('class', [])
            if isinstance(classes, list):
                if any(any(pt in cls.lower() for pt in press_terms) for cls in classes):
                    has_press = True
                    break
            elif isinstance(classes, str):
                if any(pt in classes.lower() for pt in press_terms):
                    has_press = True
                    break

    if not has_press:
        findings.append({
            "id": "SA-007",
            "title": "[Proactive] No Press/Media or Awards Section",
            "severity": "medium",
            "evidence": "No press, media coverage, or awards section detected. Third-party validation strengthens AI citation confidence.",
            "suggested_action": {
                "summary": "Create a 'Press' or 'Awards' section linking to third-party validation and PR coverage.",
                "priority": "medium"
            }
        })

    return findings

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_social_authority.py <url>")
        sys.exit(1)
        
    url = sys.argv[1]
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        findings = analyze_social_authority(soup, url, base_url)
        print(json.dumps(findings, indent=2))
        
    except Exception as e:
        print(f"Error processing {url}: {e}", file=sys.stderr)
        sys.exit(1)
