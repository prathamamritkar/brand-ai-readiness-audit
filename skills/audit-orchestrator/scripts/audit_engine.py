#!/usr/bin/env python3
"""
Brand AI-Readiness Audit Engine v2.1
Zero-dependency, deterministic, read-only.
Python 3.9+ standard library only.
"""

import argparse
import datetime
import gzip
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
import zlib
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set, Tuple

USER_AGENT = "Mozilla/5.0 (compatible; BrandAIReadinessAuditBot/2.1; +https://agentskills.io)"
AI_BOTS = {"gptbot", "claudebot", "perplexitybot", "google-extended",
           "bytespider", "ccbot", "anthropic-ai", "cohere-ai"}
FRAMEWORK_MARKERS = ["data-reactroot", "data-reactid", "__nuxt", "data-vue",
                     "ng-app", "data-nextjs-page", "data-sveltekit",
                     "data-astro-cid", "data-qid"]
UI_BRIDGE_SIGNALS = ["ai-banner", "intent-bridge", "assistant-context",
                     "chat-landing", "ref-banner"]
ANCHOR_PATTERNS = {"spec", "specification", "price", "pricing", "feature",
                   "detail", "material", "size", "review", "availability", "buy"}
HARD_TIMEOUT = 280.0


class DOMExtractor(HTMLParser):
    """Extracts text, schema, links, and structure. Counts <noscript> text as visible."""

    def __init__(self):
        super().__init__()
        self.text_chunks: List[str] = []
        self.script_content: List[str] = []
        self.inline_scripts: List[str] = []
        self.json_ld_scripts: List[str] = []
        self.element_ids: Set[str] = set()
        self.links: Set[str] = set()
        self.meta_tags: List[Dict[str, str]] = []
        self.title: str = ""
        self.canonical: str = ""
        self.og_tags: Dict[str, str] = {}
        self.semantic_counts: Dict[str, int] = {}
        self.heading_counts: Dict[str, int] = {}
        self._in_script = False
        self._in_json_ld = False
        self._in_title = False
        self._in_noscript = False
        self._script_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        if self._in_noscript:
            return
        attr = {k.lower(): (v or "") for k, v in attrs}

        if tag in {"header", "nav", "main", "article", "section", "aside", "footer"}:
            self.semantic_counts[tag] = self.semantic_counts.get(tag, 0) + 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_counts[tag] = self.heading_counts.get(tag, 0) + 1
        if attr.get("id"):
            self.element_ids.add(attr["id"])

        if tag == "script":
            self._in_script = True
            if attr.get("type", "").lower() == "application/ld+json":
                self._in_json_ld = True
            elif not attr.get("src"):
                self._script_buffer = []
        elif tag == "noscript":
            self._in_noscript = True
        elif tag == "a" and attr.get("href"):
            self.links.add(attr["href"])
        elif tag == "meta":
            name = attr.get("name", "").lower()
            prop = attr.get("property", "").lower()
            content = attr.get("content", "")
            self.meta_tags.append({"name": name, "property": prop, "content": content})
            if prop.startswith("og:"):
                self.og_tags[prop] = content
        elif tag == "link" and attr.get("rel", "").lower() == "canonical" and attr.get("href"):
            self.canonical = attr["href"]
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str):
        if tag == "script":
            if not self._in_json_ld and self._script_buffer:
                text = "".join(self._script_buffer).strip()
                if len(text) > 10:
                    self.inline_scripts.append(text)
            self._in_script = False
            self._in_json_ld = False
            self._script_buffer = []
        elif tag == "noscript":
            self._in_noscript = False
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        clean = data.strip()
        if not clean:
            return
        if self._in_json_ld:
            self.json_ld_scripts.append(clean)
        elif self._in_script:
            self._script_buffer.append(clean)
        elif self._in_title:
            self.title += clean
        else:
            self.text_chunks.append(clean)

    def get_plain_text(self) -> str:
        return " ".join(self.text_chunks)

    def get_word_count(self) -> int:
        return len(self.get_plain_text().split())

    def get_meta_robots(self) -> List[str]:
        directives: Set[str] = set()
        for meta in self.meta_tags:
            if meta.get("name") == "robots" and meta.get("content"):
                directives.update(d.strip() for d in meta["content"].lower().split(","))
        return list(directives)


class AuditEngine:
    """Deterministic orchestrator."""

    def __init__(self, base_url: str, max_pages: int = 5, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.parsed = urllib.parse.urlparse(self.base_url)
        self.domain = self.parsed.netloc or self.parsed.path
        self.max_pages = min(max_pages, 10)
        self.timeout = timeout
        self.findings: List[Dict[str, Any]] = []
        self.finding_counter = 1
        self.robots: Optional[urllib.robotparser.RobotFileParser] = None
        self.crawl_delay = 0.0
        self.page_data: Dict[str, Dict[str, Any]] = {}
        self.ssl_ctx = ssl._create_unverified_context()
        self.start_time = 0.0
        self._timed_out = False

    def _overtime(self) -> bool:
        if time.time() - self.start_time > HARD_TIMEOUT:
            if not self._timed_out:
                self._timed_out = True
                self._add_finding(
                    "Audit Curtailed by Runtime Budget",
                    "medium", "discoverability", self.base_url,
                    f"Approached {int(HARD_TIMEOUT)}s hard timeout.",
                    "Improve site TTFB to allow complete auditing.",
                    "medium"
                )
            return True
        return False

    def fetch_url(self, url: str, max_bytes: int = 2_000_000) -> Tuple[Optional[int], Dict[str, str], Optional[bytes]]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_ctx) as resp:
                status = resp.getcode()
                headers = {k.lower(): v for k, v in resp.headers.items()}
                raw = resp.read(max_bytes)
                enc = headers.get("content-encoding", "").lower()
                if "gzip" in enc:
                    try:
                        raw = gzip.decompress(raw)
                    except Exception:
                        pass
                elif "deflate" in enc:
                    try:
                        raw = zlib.decompress(raw)
                    except Exception:
                        pass
                return status, headers, raw
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, None
        except Exception:
            return None, {}, None

    def _normalize(self, url: str) -> str:
        p = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, "", "", ""))

    def _is_internal(self, url: str) -> bool:
        return urllib.parse.urlparse(url).netloc.lower() == self.parsed.netloc.lower()

    def _add_finding(self, title: str, severity: str, category: str, url: str,
                     evidence: str, action_summary: str, action_priority: str):
        fid = f"F-{self.finding_counter:03d}"
        self.finding_counter += 1
        self.findings.append({
            "id": fid,
            "title": title,
            "severity": severity.lower(),
            "category": category,
            "url": url,
            "evidence": evidence,
            "suggested_action": {
                "summary": action_summary,
                "priority": action_priority.lower()
            }
        })

    def audit_robots_txt(self):
        robots_url = f"{self.parsed.scheme}://{self.parsed.netloc}/robots.txt"
        status, _, content = self.fetch_url(robots_url)

        if status != 200 or not content:
            self._add_finding(
                "Missing or Unreachable robots.txt",
                "medium", "discoverability", robots_url,
                f"GET returned HTTP {status or 'Unreachable'}.",
                "Deploy robots.txt with explicit AI crawler policies.",
                "medium"
            )
            return

        text = content.decode("utf-8", errors="ignore")
        self.robots = urllib.robotparser.RobotFileParser()
        self.robots.parse(text.splitlines())

        blocked = [b for b in AI_BOTS if not self.robots.can_fetch(b, "/")]
        if blocked:
            self._add_finding(
                "AI Assistants Blocked in robots.txt",
                "critical", "discoverability", robots_url,
                f"Disallow detected for: {', '.join(blocked)}.",
                "Add Allow rules for verified AI user-agents.",
                "critical"
            )

        for line in text.lower().splitlines():
            if line.startswith("crawl-delay:"):
                try:
                    self.crawl_delay = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                break

    def audit_llms_txt(self):
        llms_url = f"{self.parsed.scheme}://{self.parsed.netloc}/llms.txt"
        status, _, content = self.fetch_url(llms_url)
        if status != 200 or not content:
            self._add_finding(
                "Missing /llms.txt Machine-Readable Endpoint",
                "medium", "discoverability", llms_url,
                f"GET returned HTTP {status or 'Unreachable'}.",
                "Publish /llms.txt with Markdown entity catalog.",
                "medium"
            )
            return
        decoded = content.decode("utf-8", errors="ignore").strip()
        if len(decoded) < 50 or not decoded.startswith("#"):
            self._add_finding(
                "Malformed /llms.txt Manifest",
                "medium", "discoverability", llms_url,
                f"Present but lacks Markdown hierarchy ({len(decoded)} bytes).",
                "Format with H1/H2 groupings per llms.txt spec.",
                "medium"
            )

    def crawl_and_extract(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        visited: Set[str] = {self._normalize(self.base_url)}
        queue: List[str] = [self.base_url]

        while queue and len(results) < self.max_pages:
            if self._overtime():
                break

            url = queue.pop(0)
            norm = self._normalize(url)

            if self.robots and not self.robots.can_fetch(USER_AGENT, norm):
                continue

            if self.crawl_delay > 0:
                time.sleep(self.crawl_delay)

            status, headers, content = self.fetch_url(url)
            if status != 200 or not content:
                continue

            try:
                html = content.decode("utf-8", errors="ignore")
                parser = DOMExtractor()
                parser.feed(html)

                low = html.lower()
                results[norm] = {
                    "status": status,
                    "headers": headers,
                    "parser": parser,
                    "has_framework": any(m in low for m in FRAMEWORK_MARKERS),
                    "has_ui_bridge": any(s in low for s in UI_BRIDGE_SIGNALS),
                }

                for raw in parser.links:
                    resolved = urllib.parse.urljoin(url, raw)
                    rnorm = self._normalize(resolved)
                    if self._is_internal(resolved) and rnorm not in visited:
                        path = urllib.parse.urlparse(resolved).path.lower()
                        if any(ext in path for ext in [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".css", ".js"]):
                            continue
                        visited.add(rnorm)
                        queue.append(resolved)
            except Exception:
                continue

        return results

    def _extract_schema(self, parser: DOMExtractor) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []
        for raw in parser.json_ld_scripts:
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    nodes.extend(d for d in data if isinstance(d, dict))
                elif isinstance(data, dict):
                    nodes.append(data)
            except Exception:
                continue
        return nodes

    def _has_type(self, nodes: List[Dict[str, Any]], types: Set[str]) -> bool:
        for node in nodes:
            t = str(node.get("@type", "")).lower()
            if any(ty in t for ty in types):
                return True
        return False

    def check_crawl_render(self, url: str, data: Dict[str, Any]):
        parser = data["parser"]
        headers = data["headers"]

        meta = parser.get_meta_robots()
        xrob = headers.get("x-robots-tag", "").lower()
        if "noindex" in meta or "none" in meta:
            self._add_finding(
                "Meta Robots Blocks Indexing", "critical", "discoverability", url,
                f'<meta name="robots" content={",".join(meta)}>',
                "Remove noindex/none from public pages.", "critical"
            )
        if "noindex" in xrob:
            self._add_finding(
                "X-Robots-Tag Blocks Indexing", "critical", "discoverability", url,
                f"Header: {headers['x-robots-tag']}",
                "Remove X-Robots-Tag noindex.", "critical"
            )

        words = parser.get_word_count()
        script_bytes = sum(len(s.encode("utf-8")) for s in parser.script_content)
        if words < 150 and script_bytes > 40000:
            ev = f"Static HTML: {words} words, scripts: {script_bytes} bytes."
            if data["has_framework"]:
                ev += " Hydration markers found."
            self._add_finding(
                "Client-Side Rendering Barrier", "high", "discoverability", url,
                ev, "Implement SSR or dynamic pre-rendering for AI crawlers.", "high"
            )

        if parser.semantic_counts.get("main", 0) == 0 and parser.semantic_counts.get("article", 0) == 0:
            self._add_finding(
                "Missing Semantic Landmarks", "medium", "discoverability", url,
                "No <main> or <article> tags; RAG chunking struggles.",
                "Wrap primary content in semantic elements.", "medium"
            )

        h1 = parser.heading_counts.get("h1", 0)
        if h1 == 0:
            self._add_finding(
                "Missing H1 Heading", "medium", "discoverability", url,
                "No h1 tag found.",
                "Add one descriptive h1 per page.", "medium"
            )
        elif h1 > 1:
            self._add_finding(
                "Multiple H1 Headings", "medium", "discoverability", url,
                f"Found {h1} h1 tags.",
                "Consolidate to exactly one h1.", "medium"
            )

        nodes = self._extract_schema(parser)
        if not nodes:
            self._add_finding(
                "Zero JSON-LD Structured Data", "high", "discoverability", url,
                "No application/ld+json blocks.",
                "Inject Organization, Brand, Product, Offer, BreadcrumbList schema.", "high"
            )
        else:
            has_product = self._has_type(nodes, {"product"})
            has_org = self._has_type(nodes, {"organization", "brand", "corporation"})
            text = parser.get_plain_text().lower()
            commerce = any(k in text for k in ["$", "€", "£", "₹", "buy now", "add to cart"])

            if commerce and not has_product:
                self._add_finding(
                    "Commerce Signals Without Product Schema", "high", "discoverability", url,
                    "Price/purchase text present but no Product JSON-LD.",
                    "Add Product and Offer schema with price and availability.", "high"
                )
            elif not has_product and not has_org:
                self._add_finding(
                    "Missing Core Entity Schema", "medium", "discoverability", url,
                    "JSON-LD lacks Product, Organization, or Brand.",
                    "Add primary entity definitions.", "medium"
                )

            if not self._has_type(nodes, {"breadcrumblist"}):
                self._add_finding(
                    "Missing BreadcrumbList Schema", "medium", "discoverability", url,
                    "No BreadcrumbList found.",
                    "Implement BreadcrumbList to preserve navigation context.", "medium"
                )
            if not self._has_type(nodes, {"speakablespecification"}):
                self._add_finding(
                    "Missing SpeakableSpecification Schema", "medium", "discoverability", url,
                    "No SpeakableSpecification markup.",
                    "Add cssSelector targets for key content blocks.", "medium"
                )
            if url == self.base_url and not self._has_type(nodes, {"website"}):
                self._add_finding(
                    "Missing WebSite Schema", "medium", "discoverability", url,
                    "Root page lacks WebSite JSON-LD.",
                    "Add WebSite schema with url and SearchAction.", "medium"
                )

        if not parser.og_tags.get("og:title") or not parser.og_tags.get("og:description"):
            self._add_finding(
                "Incomplete Open Graph Tags", "medium", "discoverability", url,
                f"OG keys present: {list(parser.og_tags.keys())}.",
                "Add og:title and og:description for knowledge graph consensus.", "medium"
            )

    def check_freshness(self, url: str, data: Dict[str, Any]):
        parser = data["parser"]
        headers = data["headers"]
        nodes = self._extract_schema(parser)

        has_temporal = False
        has_sameas = False
        has_org = False
        has_disambig = False

        for node in nodes:
            t = str(node.get("@type", "")).lower()
            if any(x in t for x in {"organization", "brand", "corporation", "localbusiness"}):
                has_org = True
                if node.get("sameAs"):
                    has_sameas = True
                if node.get("disambiguatingDescription"):
                    has_disambig = True
            if node.get("dateModified") or node.get("datePublished"):
                has_temporal = True

        if has_org and not has_sameas:
            self._add_finding(
                "Missing sameAs Knowledge Graph Bindings", "medium", "discoverability", url,
                "Organization/Brand schema lacks sameAs links.",
                "Link to Wikidata, Wikipedia, and authority nodes via sameAs.", "medium"
            )
        if has_org and not has_disambig:
            self._add_finding(
                "Missing disambiguatingDescription", "medium", "discoverability", url,
                "Brand entity lacks disambiguatingDescription.",
                "Add a concise statement to prevent LLM homonym conflation.", "medium"
            )
        if not has_temporal and "last-modified" not in headers:
            self._add_finding(
                "Missing Temporal Freshness Signals", "medium", "discoverability", url,
                "No dateModified/datePublished in schema and no Last-Modified header.",
                "Add ISO 8601 timestamps in JSON-LD and HTTP headers.", "medium"
            )

        if not parser.canonical and (parser.heading_counts.get("h1", 0) > 0 or parser.get_word_count() > 200):
            self._add_finding(
                "Missing Canonical Tag", "medium", "discoverability", url,
                "Content page lacks rel=canonical.",
                "Add self-referencing canonical tags to prevent duplicate fragmentation.", "medium"
            )

    def check_engagement(self, url: str, data: Dict[str, Any]):
        parser = data["parser"]

        found = {eid for eid in parser.element_ids if any(p in eid.lower() for p in ANCHOR_PATTERNS)}
        if not found:
            self._add_finding(
                "Absence of Semantic Deep-Fragment Anchors", "medium", "engagement", url,
                "No element IDs match high-intent patterns (#specs, #pricing, etc.).",
                "Implement semantic ID anchors for key specification blocks.", "medium"
            )

        has_ref = any(sig in sc.lower() for sig in {"document.referrer", "chatgpt", "perplexity", "claude", "intent-bridge"}
                      for sc in parser.inline_scripts)
        has_edge = any(h in data["headers"] for h in {"cf-worker", "x-fastly-ttl", "x-vercel-id", "x-render-origin-server"})

        if not has_ref and not data["has_ui_bridge"] and not has_edge:
            self._add_finding(
                "No Conversational Referrer Handling", "medium", "engagement", url,
                "No inline script referrer detection, intent-bridge UI, or Edge worker headers.",
                "Implement Edge middleware or client-side referrer parsing for AI traffic.", "medium"
            )

        if parser.heading_counts.get("h1", 0) == 0:
            self._add_finding(
                "Weak Post-Click Orientation", "medium", "engagement", url,
                "Missing h1 heading; AI-referred visitors lose immediate context.",
                "Add a descriptive h1 matching likely conversational query intent.", "medium"
            )

    def post_crawl_taxonomy_audit(self):
        prefix_to_cats: Dict[str, Set[str]] = {}
        for url, data in self.page_data.items():
            parser = data["parser"]
            path = urllib.parse.urlparse(url).path
            seg = [s for s in path.split("/") if s]
            prefix = seg[0] if seg else ""

            for node in self._extract_schema(parser):
                if "product" in str(node.get("@type", "")).lower():
                    cat = node.get("category") or node.get("additionalType")
                    if cat:
                        prefix_to_cats.setdefault(prefix, set()).add(str(cat).lower())

        for prefix, cats in prefix_to_cats.items():
            if len(cats) > 1:
                self._add_finding(
                    "Cross-Category Semantic Bleed Risk", "medium", "engagement", self.base_url,
                    f"Prefix '/{prefix}/' holds divergent categories: {', '.join(sorted(cats))}.",
                    "Isolate lines under dedicated namespaces (e.g., /performance/ vs /lifestyle/).", "medium"
                )

    def audit_sitemap(self):
        sitemap_url = f"{self.parsed.scheme}://{self.parsed.netloc}/sitemap.xml"
        status, _, content = self.fetch_url(sitemap_url)
        if status != 200 or not content:
            self._add_finding(
                "Missing or Unreachable Sitemap", "medium", "discoverability", sitemap_url,
                f"GET returned HTTP {status or 'Unreachable'}.",
                "Publish sitemap.xml with ISO 8601 lastmod tags.", "medium"
            )
            return

        try:
            root = ET.fromstring(content)
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            tag = root.tag.lower()

            if "sitemapindex" in tag:
                items = root.findall(".//ns:sitemap", ns) or root.findall(".//sitemap")
            else:
                items = root.findall(".//ns:url", ns) or root.findall(".//url")

            if items:
                missing = sum(1 for el in items if el.find("ns:lastmod", ns) is None and el.find("lastmod") is None)
                if missing / len(items) > 0.5:
                    self._add_finding(
                        "Sitemap Lacks lastmod Signals", "medium", "discoverability", sitemap_url,
                        f"{missing}/{len(items)} entries missing <lastmod>.",
                        "Inject dynamic ISO 8601 lastmod tags into sitemap.", "medium"
                    )
        except Exception:
            pass

    def audit_legacy_urls(self):
        probes: Set[str] = set()
        for url in list(self.page_data.keys())[:3]:
            path = urllib.parse.urlparse(url).path.rstrip("/")
            if path and path != "/":
                probes.add(f"{path}-old")
                probes.add(f"/archive{path}")

        stale: List[str] = []
        for probe in list(probes)[:4]:
            if self._overtime():
                break
            test = f"{self.parsed.scheme}://{self.parsed.netloc}{probe}"
            st, _, _ = self.fetch_url(test)
            if st == 200:
                stale.append(probe)

        if stale:
            self._add_finding(
                "Legacy URLs Returning HTTP 200", "medium", "discoverability", self.base_url,
                f"Heuristic probes returned 200: {', '.join(stale[:3])}.",
                "Return HTTP 301 (with canonical) or HTTP 410 Gone for discontinued items.", "medium"
            )

    def run(self) -> Dict[str, Any]:
        self.start_time = time.time()

        self.audit_robots_txt()
        self.audit_llms_txt()
        self.page_data = self.crawl_and_extract()

        if not self.page_data:
            self._add_finding(
                "No Crawlable Pages Found", "critical", "discoverability", self.base_url,
                "Root inaccessible or all pages blocked.",
                "Ensure 200 OK responses and permissive robots.txt.", "critical"
            )
            return self._compile_report()

        for url, data in self.page_data.items():
            if self._overtime():
                break
            self.check_crawl_render(url, data)
            self.check_freshness(url, data)
            self.check_engagement(url, data)

        self.audit_sitemap()
        self.post_crawl_taxonomy_audit()
        self.audit_legacy_urls()

        return self._compile_report()

    def _compile_report(self) -> Dict[str, Any]:
        order = {"critical": 0, "high": 1, "medium": 2}
        self.findings.sort(key=lambda x: order.get(x["severity"], 3))

        summary = {
            "total_findings": len(self.findings),
            "critical": sum(1 for f in self.findings if f["severity"] == "critical"),
            "high": sum(1 for f in self.findings if f["severity"] == "high"),
            "medium": sum(1 for f in self.findings if f["severity"] == "medium")
        }

        return {
            "site": self.domain,
            "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": summary,
            "findings": self.findings
        }


def main():
    p = argparse.ArgumentParser(description="Brand AI-Readiness Audit Engine v2.1")
    p.add_argument("--url", required=True)
    p.add_argument("--max-pages", type=int, default=5)
    p.add_argument("--out", help="Output JSON file path")
    args = p.parse_args()

    engine = AuditEngine(base_url=args.url, max_pages=args.max_pages)
    report = engine.run()

    out = json.dumps(report, indent=2)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out)
            print(f"Audit complete: {report['summary']['total_findings']} findings -> {args.out}")
        except Exception as e:
            print(f"Write error: {e}", file=sys.stderr)
            print(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
