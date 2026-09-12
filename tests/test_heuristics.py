import sys
import os
import importlib.util
from bs4 import BeautifulSoup
import urllib.robotparser

def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

BASE_DIR = r"d:\projects\brand-ai-readiness-audit"

# Load modules
cr_module = load_module("check_crawl_render", os.path.join(BASE_DIR, r"skills\crawl-render-audit\scripts\check_crawl_render.py"))
disc_module = load_module("check_discoverability", os.path.join(BASE_DIR, r"skills\discoverability-audit\scripts\check_discoverability.py"))
fresh_module = load_module("check_freshness", os.path.join(BASE_DIR, r"skills\freshness-signals\scripts\check_freshness.py"))
eng_module = load_module("check_engagement", os.path.join(BASE_DIR, r"skills\engagement-audit\scripts\check_engagement.py"))
st_module = load_module("check_security_trust", os.path.join(BASE_DIR, r"skills\security-trust-audit\scripts\check_security_trust.py"))
orch_module = load_module("run_audit", os.path.join(BASE_DIR, r"skills\audit-orchestrator\scripts\run_audit.py"))

def analyze_crawl_render(*args, **kwargs): return cr_module.analyze_crawl_render(*args, **kwargs)
def analyze_discoverability(*args, **kwargs): return disc_module.analyze_discoverability(*args, **kwargs)
def analyze_freshness(*args, **kwargs): return fresh_module.analyze_freshness(*args, **kwargs)
def analyze_engagement(*args, **kwargs): return eng_module.analyze_engagement(*args, **kwargs)
def analyze_security_trust(*args, **kwargs): return st_module.analyze_security_trust(*args, **kwargs)
def _compute_readiness_score(*args, **kwargs): return orch_module._compute_readiness_score(*args, **kwargs)
def _validate_finding(*args, **kwargs): return orch_module._validate_finding(*args, **kwargs)

# --- Crawl & Render Tests ---

def test_cr001_ai_bots_blocked():
    html = "<html><body><h1>Test</h1></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: GPTBot", "Disallow: /"])
    
    findings = analyze_crawl_render(soup, rp, {}, "https://example.com/", "https://example.com")
    cr001 = [f for f in findings if f['id'] == 'CR-001']
    assert len(cr001) > 0
    assert cr001[0]['severity'] == 'critical'

def test_cr007_images_missing_alt():
    html = '<html><body><img src="test.jpg"></body></html>'
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_crawl_render(soup, None, {}, "https://example.com/", "https://example.com")
    cr007 = [f for f in findings if f['id'] == 'CR-007']
    assert len(cr007) > 0

def test_cr002_meta_noindex():
    html = '<html><head><meta name="robots" content="noindex"></head><body></body></html>'
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_crawl_render(soup, None, {}, "https://example.com/", "https://example.com")
    cr002 = [f for f in findings if f['id'] == 'CR-002']
    assert len(cr002) > 0

# --- Discoverability Tests ---

def test_disc001_no_jsonld():
    html = "<html><body><h1>Test</h1></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_discoverability(soup, "https://example.com/")
    disc001 = [f for f in findings if f['id'] == 'DISC-001']
    assert len(disc001) > 0

def test_disc004_no_sameas():
    html = '''<html><head><script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Test"}
    </script></head><body></body></html>'''
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_discoverability(soup, "https://example.com/")
    disc004 = [f for f in findings if f['id'] == 'DISC-004']
    assert len(disc004) > 0

def test_disc006_no_canonical():
    html = "<html><head></head><body></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_discoverability(soup, "https://example.com/")
    disc006 = [f for f in findings if f['id'] == 'DISC-006']
    assert len(disc006) > 0

def test_disc007_valid_title():
    html = '<html><head><title>Test Title That Is Long Enough</title><meta name="description" content="A valid description"></head><body></body></html>'
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_discoverability(soup, "https://example.com/")
    disc007 = [f for f in findings if f['id'] == 'DISC-007']
    assert len(disc007) == 0

# --- Freshness Tests ---

def test_fr001_no_date_markup():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_freshness(soup)
    fr001 = [f for f in findings if f['id'] == 'FR-001']
    assert len(fr001) > 0

def test_fr002_stale_copyright():
    html = "<html><body><footer>Copyright 2020</footer></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_freshness(soup)
    fr002 = [f for f in findings if f['id'] == 'FR-002']
    assert len(fr002) > 0

def test_fr005_no_attribution():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_freshness(soup)
    fr005 = [f for f in findings if f['id'] == 'FR-005']
    assert len(fr005) > 0

# --- Engagement Tests ---

def test_eng001_no_h1():
    html = "<html><body><h2>Test</h2></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_engagement(soup, "https://example.com/")
    eng001 = [f for f in findings if f['id'] == 'ENG-001']
    assert len(eng001) > 0

def test_eng004_no_landmarks():
    html = "<html><body><div>Test</div></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_engagement(soup, "https://example.com/")
    eng004 = [f for f in findings if f['id'] == 'ENG-004']
    assert len(eng004) > 0

def test_eng008_no_lang():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_engagement(soup, "https://example.com/")
    eng008 = [f for f in findings if f['id'] == 'ENG-008']
    assert len(eng008) > 0

# --- Orchestrator Tests ---

def test_readiness_score_perfect():
    findings = []
    assert _compute_readiness_score(findings) == 100

def test_readiness_score_critical():
    findings = [{'severity': 'critical', 'phase': 'Crawl'}]
    assert _compute_readiness_score(findings) == 75

def test_readiness_score_mixed():
    findings = [
        {'severity': 'critical', 'phase': 'Crawl'},
        {'severity': 'high', 'phase': 'Crawl'},
        {'severity': 'high', 'phase': 'Crawl'},
        {'severity': 'medium', 'phase': 'Crawl'},
        {'severity': 'medium', 'phase': 'Crawl'},
        {'severity': 'medium', 'phase': 'Crawl'}
    ]
    # 1 critical (25), 2 high (2*10=20), 3 medium (3*3=9) => 100 - 54 = 46
    assert _compute_readiness_score(findings) == 46

def test_validate_finding_valid():
    finding = {
        'id': 'TEST-001',
        'title': 'Test Finding',
        'severity': 'high',
        'evidence': 'Evid',
        'suggested_action': {
            'summary': 'Fix the thing',
            'priority': 'high'
        }
    }
    assert _validate_finding(finding) == True

def test_validate_finding_missing_field():
    finding = {
        'id': 'TEST-001',
        'title': 'Test Finding',
        'severity': 'high',
        'phase': 'Crawl',
        'description': 'Desc'
        # missing evidence
    }
    assert _validate_finding(finding) == False

# --- Clean Page Test (regression) ---

def test_clean_page_minimal_findings():
    html = """
    <html lang="en">
    <head>
        <title>Brand AI Readiness Audit - Modern Title</title>
        <meta name="description" content="A valid description that is long enough to pass.">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="canonical" href="https://example.com/">
        <meta property="og:title" content="Test">
        <meta property="og:description" content="Test description">
        <meta property="og:type" content="website">
        <meta property="og:image" content="https://example.com/img.jpg">
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": "https://example.com/#org",
            "name": "Test Corp",
            "sameAs": ["https://twitter.com/test"],
            "url": "https://example.com/"
        }
        </script>
    </head>
    <body>
        <header>
            <nav><a href="/">Home</a> <a href="/about">About</a></nav>
        </header>
        <main>
            <h1>Welcome to Test Corp</h1>
            <p>This is a comprehensive introduction paragraph that provides substantial
            context about what Test Corp does and why it matters. We specialize in
            building innovative solutions for modern businesses that need to establish
            strong AI visibility across all major platforms and search engines. Our
            team of dedicated experts works tirelessly to ensure your brand is
            discoverable by both human visitors and AI assistants alike.</p>
            <h2>Our Services</h2>
            <p>We offer a wide range of professional services designed to help
            businesses improve their online presence and AI readiness. From structured
            data implementation to content optimization, we cover every aspect of
            modern digital visibility. Our approach is evidence-based and results-driven,
            ensuring measurable improvements in how AI systems perceive and cite
            your brand in their responses to user queries.</p>
            <h2>Why Choose Us</h2>
            <ul>
                <li>Expert team with years of experience</li>
                <li>Proven track record of successful implementations</li>
                <li>Comprehensive audit methodology</li>
            </ul>
            <img src="test.jpg" alt="A detailed chart showing our performance metrics">
            <time datetime="2026-09-06">Sep 6, 2026</time>
        </main>
        <footer>
            <p>Copyright 2026 Test Corp. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, 'html.parser')

    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Allow: /"])

    cr_findings = analyze_crawl_render(soup, rp, {}, "https://example.com/", "https://example.com")
    disc_findings = analyze_discoverability(soup, "https://example.com/")
    fr_findings = analyze_freshness(soup, {}, "https://example.com/", "")
    eng_findings = analyze_engagement(soup, "https://example.com/")
    st_findings = analyze_security_trust(soup, {"Strict-Transport-Security": "max-age=31536000", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin-when-cross-origin"}, "https://example.com/", "https://example.com")

    all_findings = cr_findings + disc_findings + fr_findings + eng_findings + st_findings

    severe_findings = [f for f in all_findings if f['severity'] in ('critical', 'high')]
    assert len(severe_findings) == 0, f"Found severe findings: {severe_findings}"

# --- Security & Trust Tests ---

def test_st001_http_not_https():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_security_trust(soup, {}, "http://example.com", "http://example.com")
    st001 = [f for f in findings if f['id'] == 'ST-001']
    assert len(st001) > 0
    assert st001[0]['severity'] == 'critical'

def test_st002_missing_hsts():
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    # HTTPS but no HSTS header
    findings = analyze_security_trust(soup, {}, "https://example.com", "https://example.com")
    st002 = [f for f in findings if f['id'] == 'ST-002']
    assert len(st002) > 0
    assert st002[0]['severity'] == 'high'

def test_st006_no_privacy_links():
    html = "<html><body><a href='/about'>About</a><a href='/contact'>Contact</a></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_security_trust(soup, {}, "https://example.com", "https://example.com")
    st006 = [f for f in findings if f['id'] == 'ST-006']
    assert len(st006) > 0

def test_st006_has_privacy_link():
    html = "<html><body><footer><a href='/privacy'>Privacy Policy</a></footer></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    findings = analyze_security_trust(soup, {}, "https://example.com", "https://example.com")
    st006 = [f for f in findings if f['id'] == 'ST-006']
    assert len(st006) == 0
