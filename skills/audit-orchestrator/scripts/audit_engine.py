#!/usr/bin/env python3
"""
Brand AI-Readiness Audit Engine v3.0
Deterministic, read-only. Python 3.9+ standard library only.
Findings tagged with gap_type: indexing | citation | engagement.
"""

import argparse
import datetime
import gzip
import json
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

USER_AGENT = "Mozilla/5.0 (compatible; BrandAIReadinessAuditBot/3.0; +https://agentskills.io)"
AI_BOTS = {"gptbot", "claudebot", "perplexitybot", "google-extended",
           "bytespider", "ccbot", "anthropic-ai", "cohere-ai"}
FRAMEWORK_MARKERS = ["data-reactroot", "data-reactid", "__nuxt", "data-vue",
                     "ng-app", "data-nextjs-page", "data-sveltekit",
                     "data-astro-cid", "data-qid"]
# Pattern-driven; no hardcoded site-specific class names
REFERRER_PATTERNS = ["document.referrer", "urlsearchparams", "location.search",
                     "sessionstorage", "localstorage.getitem"]
TRANSACTIONAL_VERBS = ["buy", "order", "get", "download", "contact",
                       "start", "try", "sign up", "request", "book", "purchase"]
HARD_TIMEOUT = 300.0


class DOMExtractor(HTMLParser):
    """Extracts text, schema, links, and structure."""

    def __init__(self):
        super().__init__()
        self.text_chunks: List[str] = []
        self.noscript_chunks: List[str] = []
        self.external_script_bytes: int = 0
        self.inline_scripts: List[str] = []
        self.json_ld_scripts: List[str] = []
        self.element_ids: List[str] = []  # ordered list preserves DOM position
        self.links: Set[str] = set()
        self.meta_tags: List[Dict[str, str]] = []
        self.title: str = ""
        self.meta_description: str = ""
        self.canonical: str = ""
        self.hreflang_tags: List[Dict[str, str]] = []
        self.og_tags: Dict[str, str] = {}
        self.semantic_counts: Dict[str, int] = {}
        self.heading_counts: Dict[str, int] = {}
        self.heading_sequence: List[int] = []
        self.breaker_count: int = 0
        self.block_element_count: int = 0  # proxy for DOM depth
        self.transactional_elements: List[Tuple[str, int]] = []  # (text, dom_position)
        self.images: List[Dict[str, str]] = []
        self._in_script = False
        self._in_json_ld = False
        self._in_title = False
        self._in_noscript = False
        self._script_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr = {k.lower(): (v or "") for k, v in attrs}

        if not self._in_noscript:
            if tag in {"header", "nav", "main", "article", "section", "aside", "footer",
                       "div", "p", "li", "tr"}:
                self.semantic_counts[tag] = self.semantic_counts.get(tag, 0) + 1
                self.block_element_count += 1
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                self.heading_counts[tag] = self.heading_counts.get(tag, 0) + 1
                self.heading_sequence.append(int(tag[1]))
            if tag in {"ul", "ol", "table", "blockquote"}:
                self.breaker_count += 1
            if attr.get("id"):
                self.element_ids.append(attr["id"])

            if tag == "script":
                self._in_script = True
                if attr.get("type", "").lower() == "application/ld+json":
                    self._in_json_ld = True
                elif attr.get("src"):
                    self.external_script_bytes += len(attr["src"].encode("utf-8")) * 50
                else:
                    self._script_buffer = []
            elif tag in {"a", "button"}:
                href = attr.get("href", "")
                if href:
                    self.links.add(href)
                label = (attr.get("aria-label", "") or "").lower()
                self.transactional_elements.append((
                    label, self.block_element_count
                ))
            elif tag == "meta":
                name = attr.get("name", "").lower()
                prop = attr.get("property", "").lower()
                content = attr.get("content", "")
                self.meta_tags.append({"name": name, "property": prop, "content": content})
                if prop.startswith("og:"):
                    self.og_tags[prop] = content
                if name == "description":
                    self.meta_description = content
            elif tag == "link":
                rel = attr.get("rel", "").lower()
                if rel == "canonical" and attr.get("href"):
                    self.canonical = attr["href"]
                elif rel == "alternate" and attr.get("hreflang"):
                    self.hreflang_tags.append({
                        "hreflang": attr["hreflang"],
                        "href": attr.get("href", "")
                    })
            elif tag == "title":
                self._in_title = True
            elif tag == "img":
                self.images.append({
                    "src": attr.get("src", ""),
                    "alt": attr.get("alt", "")
                })
        elif tag == "noscript":
            pass  # handled in endtag

        if tag == "noscript":
            self._in_noscript = True

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
            # noscript text IS counted (SSR fallbacks); links inside are excluded
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
        elif self._in_noscript:
            self.noscript_chunks.append(clean)
        else:
            self.text_chunks.append(clean)

    def get_plain_text(self) -> str:
        return " ".join(self.text_chunks)

    def get_word_count(self) -> int:
        return len(self.get_plain_text().split())

    def get_noscript_text(self) -> str:
        return " ".join(self.noscript_chunks)

    def get_meta_robots(self) -> List[str]:
        directives: Set[str] = set()
        for meta in self.meta_tags:
            if meta.get("name") == "robots" and meta.get("content"):
                directives.update(d.strip() for d in meta["content"].lower().split(","))
        return list(directives)


class AuditEngine:
    """Deterministic orchestrator."""

    def __init__(self, base_url: str, max_pages: int = 5, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.parsed = urllib.parse.urlparse(self.base_url)
        self.domain = self.parsed.netloc or self.parsed.path
        self.max_pages = min(max_pages, 10)
        self.timeout = timeout
        self.findings: List[Dict[str, Any]] = []
        self.finding_counter = 1
        self._seen_checks: Set[str] = set()  # dedup by (url, check_id)
        self.robots: Optional[urllib.robotparser.RobotFileParser] = None
        self.crawl_delay = 0.0
        self.page_data: Dict[str, Dict[str, Any]] = {}
        self.crawl_errors: List[Dict[str, str]] = []
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
                    f"Approached {int(HARD_TIMEOUT)}s total runtime budget; remaining checks skipped.",
                    "Improve site TTFB and reduce crawl-delay to allow complete auditing.",
                    "medium", "indexing", "site"
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
            raw = None
            try:
                raw = e.read(max_bytes)
            except Exception:
                pass
            return e.code, {k.lower(): v for k, v in e.headers.items()}, raw
        except Exception:
            return None, {}, None

    def _normalize(self, url: str) -> str:
        p = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, "", "", ""))

    def _is_internal(self, url: str) -> bool:
        return urllib.parse.urlparse(url).netloc.lower() == self.parsed.netloc.lower()

    def _add_finding(self, title: str, severity: str, category: str, url: str,
                     evidence: str, action_summary: str, action_priority: str,
                     gap_type: str = "citation", scope: str = "page",
                     check_id: str = ""):
        dedup_key = f"{url}::{check_id or title}"
        if dedup_key in self._seen_checks:
            return
        self._seen_checks.add(dedup_key)
        fid = f"F-{self.finding_counter:03d}"
        self.finding_counter += 1
        self.findings.append({
            "id": fid,
            "title": title,
            "severity": severity.lower(),
            "gap_type": gap_type,
            "category": category,
            "url": url,
            "evidence": evidence,
            "suggested_action": {
                "summary": action_summary,
                "priority": action_priority.lower(),
                "scope": scope
            }
        })

    def audit_robots_txt(self):
        robots_url = f"{self.parsed.scheme}://{self.parsed.netloc}/robots.txt"
        status, _, content = self.fetch_url(robots_url)

        if status != 200 or not content:
            self._add_finding(
                "Missing or Unreachable robots.txt",
                "medium", "discoverability", robots_url,
                f"GET returned HTTP {status or 'Unreachable'}. AI crawler posture unknown.",
                "Deploy robots.txt with explicit Allow/Disallow directives for AI crawlers.",
                "medium", "indexing", "site", "robots_txt_missing"
            )
            return

        text = content.decode("utf-8", errors="ignore")
        self.robots = urllib.robotparser.RobotFileParser()
        self.robots.parse(text.splitlines())

        blocked = [b for b in AI_BOTS if not self.robots.can_fetch(b, "/")]
        if blocked:
            self._add_finding(
                "AI Crawlers Blocked in robots.txt",
                "critical", "discoverability", robots_url,
                f"Disallow on root detected for: {', '.join(sorted(blocked))}.",
                "Add explicit Allow: / rules for each blocked AI user-agent token.",
                "critical", "indexing", "site", "robots_ai_blocked"
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
                "Missing /llms.txt Machine-Readable Manifest",
                "medium", "discoverability", llms_url,
                f"GET returned HTTP {status or 'Unreachable'}.",
                "Publish /llms.txt — a Markdown-structured entity catalog for AI crawlers.",
                "medium", "citation", "site", "llms_txt_missing"
            )
            return
        decoded = content.decode("utf-8", errors="ignore").strip()
        first_line = decoded.splitlines()[0] if decoded else ""
        if len(decoded) < 50 or not decoded.startswith("#"):
            self._add_finding(
                "Malformed /llms.txt Manifest",
                "medium", "discoverability", llms_url,
                f"Present ({len(decoded)} bytes) but body does not start with '#'. First line: {first_line!r}",
                "Format /llms.txt with # H1 brand name and ## H2 section groupings.",
                "medium", "citation", "site", "llms_txt_malformed"
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
                time.sleep(min(self.crawl_delay, 5.0))  # cap to avoid budget bleed

            status, headers, content = self.fetch_url(url)
            low_body = content.decode("utf-8", errors="ignore").lower() if content else ""
            is_bot_blocked = (
                status in (403, 429) or
                "cf-mitigated" in headers or
                any(sig in low_body for sig in ["challenge-platform", "cf-browser-verification", "attention required! | cloudflare", "datadome", "perimeterx", "captcha-delivery", "please verify you are a human"]) or
                ("cloudflare" in headers.get("server", "").lower() and status in (403, 503))
            )
            if is_bot_blocked:
                self._add_finding(
                    "Site Returned Bot-Block / CAPTCHA Response",
                    "critical", "discoverability", url,
                    f"HTTP {status} with bot-challenge signature detected. Server: {headers.get('server', 'N/A')}, Cloudflare: {bool('cf-ray' in headers)}. Automated AI crawlers (GPTBot, ClaudeBot, Perplexity) cannot access content.",
                    "Configure WAF / CDN edge rules to permit verified AI bot user-agents and prevent CAPTCHA walls on public landing pages.",
                    "high", "indexing", "site", "bot_block_waf"
                )

            if status != 200 or not content:
                self.crawl_errors.append({"url": url, "error": f"HTTP {status or 'Unreachable'}"})
                continue

            try:
                html = content.decode("utf-8", errors="ignore")
                parser = DOMExtractor()
                parser.feed(html)

                low = html.lower()
                has_framework = any(m in low for m in FRAMEWORK_MARKERS)
                results[norm] = {
                    "url": url,
                    "status": status,
                    "headers": headers,
                    "parser": parser,
                    "schema_nodes": None,
                    "malformed_ld": [],  # populated by _get_schema
                    "has_framework": has_framework,
                }

                for raw in parser.links:
                    resolved = urllib.parse.urljoin(url, raw)
                    rnorm = self._normalize(resolved)
                    if self._is_internal(resolved) and rnorm not in visited:
                        path = urllib.parse.urlparse(resolved).path.lower()
                        if any(ext in path for ext in [".jpg", ".jpeg", ".png", ".gif",
                                                       ".pdf", ".zip", ".css", ".js", ".svg",
                                                       ".webp", ".woff", ".woff2"]):
                            continue
                        visited.add(rnorm)
                        queue.append(resolved)
            except Exception:
                continue

        return results

    def _get_schema(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if data["schema_nodes"] is None:
            nodes: List[Dict[str, Any]] = []
            malformed: List[str] = []
            for raw in data["parser"].json_ld_scripts:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        nodes.extend(d for d in parsed if isinstance(d, dict))
                    elif isinstance(parsed, dict):
                        # unwrap @graph if present
                        if "@graph" in parsed and isinstance(parsed["@graph"], list):
                            nodes.extend(d for d in parsed["@graph"] if isinstance(d, dict))
                        else:
                            nodes.append(parsed)
                except (json.JSONDecodeError, ValueError) as e:
                    malformed.append(f"{str(e)[:80]} | snippet: {raw[:100]!r}")
            data["schema_nodes"] = nodes
            data["malformed_ld"] = malformed
        return data["schema_nodes"]

    def _has_type(self, nodes: List[Dict[str, Any]], types: Set[str]) -> bool:
        for node in nodes:
            t = str(node.get("@type", "")).lower()
            if any(ty in t for ty in types):
                return True
        return False

    def check_crawl_render(self, url: str, data: Dict[str, Any]):
        parser = data["parser"]
        headers = data["headers"]
        words = parser.get_word_count()

        # --- Indexing checks ---
        meta = parser.get_meta_robots()
        xrob = headers.get("x-robots-tag", "").lower()
        if "noindex" in meta or "none" in meta:
            self._add_finding(
                "Meta Robots Blocks Indexing", "critical", "discoverability", url,
                f'<meta name="robots" content="{",".join(meta)}">',
                "Remove noindex/none from public pages.",
                "critical", "indexing", "page", f"meta_noindex:{url}"
            )
        if "noindex" in xrob:
            self._add_finding(
                "X-Robots-Tag Blocks Indexing", "critical", "discoverability", url,
                f"X-Robots-Tag: {headers['x-robots-tag']}",
                "Remove noindex directive from X-Robots-Tag header.",
                "critical", "indexing", "page", f"xrobot_noindex:{url}"
            )

        script_bytes = parser.external_script_bytes + sum(
            len(s.encode("utf-8")) for s in parser.inline_scripts
        )
        if words < 150 and script_bytes > 40000:
            ev = f"Visible text: {words} words; script payload: {script_bytes} bytes."
            if data["has_framework"]:
                ev += " Framework hydration markers detected in raw HTML."
            self._add_finding(
                "Client-Side Rendering Barrier", "high", "discoverability", url,
                ev, "Implement SSR or pre-rendering so crawlers receive static HTML.",
                "high", "indexing", "site", f"csr_barrier:{url}"
            )

        canonical = parser.canonical
        if canonical and words > 100:
            norm_canon = self._normalize(canonical)
            norm_current = self._normalize(url)
            if norm_canon != norm_current:
                self._add_finding(
                    "Canonical Points Away from Page", "medium", "discoverability", url,
                    f"rel=canonical href='{canonical}' differs from current URL '{url}'.",
                    "Ensure canonical points to the authoritative URL for this content.",
                    "medium", "indexing", "page", f"canonical_drift:{url}"
                )
        elif not canonical and words > 100:
            self._add_finding(
                "Missing Canonical Tag", "medium", "discoverability", url,
                "Content page (>100 words) lacks rel=canonical link tag.",
                "Add a self-referencing canonical tag on every content page.",
                "medium", "indexing", "page", f"canonical_missing:{url}"
            )

        # --- Citation checks ---
        nodes = self._get_schema(data)
        for err in data.get("malformed_ld", []):
            self._add_finding(
                "Malformed JSON-LD Block", "medium", "discoverability", url,
                f"JSON parse failed: {err}",
                "Validate JSON-LD blocks with schema.org validator; fix syntax errors.",
                "medium", "citation", "page", f"malformed_ld:{url}:{err[:40]}"
            )

        if not nodes and not data.get("malformed_ld"):
            self._add_finding(
                "Zero JSON-LD Structured Data", "high", "discoverability", url,
                "No application/ld+json blocks found.",
                "Add at minimum Organization and BreadcrumbList schema; add Product/Offer on commerce pages.",
                "high", "citation", "page", f"no_jsonld:{url}"
            )
        elif nodes:
            has_product = self._has_type(nodes, {"product"})
            has_org = self._has_type(nodes, {"organization", "brand", "corporation"})
            text = parser.get_plain_text().lower()
            import re as _re
            commerce = bool(_re.search(r'[$€£₹]\s*\d|buy now|add to cart|shop now', text))

            if commerce and not has_product:
                self._add_finding(
                    "Commerce Signals Without Product Schema", "high", "discoverability", url,
                    "Price or purchase-intent text detected but no Product/Offer JSON-LD.",
                    "Add Product with Offer (price, priceCurrency, availability) schema.",
                    "high", "citation", "page", f"commerce_no_schema:{url}"
                )

            if not self._has_type(nodes, {"breadcrumblist"}) and url != self.base_url:
                self._add_finding(
                    "Missing BreadcrumbList Schema", "medium", "discoverability", url,
                    "No BreadcrumbList found on non-root page.",
                    "Add BreadcrumbList to preserve navigation context for AI extractors.",
                    "medium", "citation", "page", f"no_breadcrumb:{url}"
                )
            if url == self.base_url and not self._has_type(nodes, {"website"}):
                self._add_finding(
                    "Missing WebSite Schema on Root", "medium", "discoverability", url,
                    "Root page lacks WebSite JSON-LD.",
                    "Add WebSite schema with url and potentialAction SearchAction.",
                    "medium", "citation", "site", "no_website_schema"
                )

        if parser.semantic_counts.get("main", 0) == 0 and parser.semantic_counts.get("article", 0) == 0:
            self._add_finding(
                "Missing Semantic Landmarks", "medium", "discoverability", url,
                "No <main> or <article> element; AI RAG chunkers struggle with undifferentiated content.",
                "Wrap primary content in <main> or <article>.",
                "medium", "citation", "page", f"no_landmarks:{url}"
            )

        h1 = parser.heading_counts.get("h1", 0)
        if h1 == 0:
            self._add_finding(
                "Missing H1 Heading", "medium", "discoverability", url,
                "No <h1> tag found.",
                "Add one descriptive <h1> per page that reflects the primary topic.",
                "medium", "citation", "page", f"no_h1:{url}"
            )
        elif h1 > 1:
            self._add_finding(
                "Multiple H1 Headings", "medium", "discoverability", url,
                f"{h1} <h1> tags found; ambiguous primary topic for AI extractors.",
                "Consolidate to exactly one <h1>.",
                "medium", "citation", "page", f"multi_h1:{url}"
            )

        gaps = []
        prev = None
        for lvl in parser.heading_sequence:
            if prev is not None and lvl > prev + 1:
                gaps.append(f"h{prev}->h{lvl}")
            prev = lvl
        if gaps:
            self._add_finding(
                "Heading Level Hierarchy Gaps", "medium", "discoverability", url,
                f"Heading hierarchy skips levels ({', '.join(gaps[:3])}). Skipping heading levels confuses AST markdown generators and AI outline extractors.",
                "Structure headings sequentially (e.g. h1 followed by h2, then h3) without jumping down multiple levels.",
                "medium", "citation", "page", f"heading_gaps:{url}"
            )

        if urllib.parse.urlparse(url).scheme.lower() != "https":
            self._add_finding(
                "HTTPS Not Enforced", "critical", "discoverability", url,
                f"Page served over unencrypted HTTP: '{url}'. Search engines and AI citation engines downrank or filter non-HTTPS sources for security and data integrity.",
                "Enforce HTTPS with automatic 301 redirects and a valid TLS certificate.",
                "high", "indexing", "site", "no_https"
            )

        if len(parser.images) >= 3:
            missing_alt = sum(1 for img in parser.images if len(img.get("alt", "").strip().split()) < 2)
            if missing_alt >= 3 and (missing_alt / len(parser.images)) >= 0.5:
                self._add_finding(
                    "Facts Locked in Images Without Substantive Alt Text",
                    "medium", "discoverability", url,
                    f"{missing_alt} of {len(parser.images)} images lack substantive alt text (>= 2 words). Uncaptioned raster images prevent text-based AI search engines from indexing key facts, diagrams, or specifications.",
                    "Add descriptive, factual alt attributes to informative images. Explicitly mark decorative graphics with alt=\"\" and role=\"presentation\".",
                    "medium", "citation", "page", f"missing_alt:{url}"
                )

        if not parser.title:
            self._add_finding(
                "Missing <title> Tag", "high", "discoverability", url,
                "<title> element absent or empty.",
                "Add a descriptive <title>; it is the primary AI snippet surface.",
                "high", "citation", "page", f"no_title:{url}"
            )

        if not parser.meta_description:
            self._add_finding(
                "Missing Meta Description", "medium", "discoverability", url,
                "<meta name=\"description\"> absent or empty.",
                "Add a 120–160 character meta description; used by AI for answer context.",
                "medium", "citation", "page", f"no_meta_desc:{url}"
            )

        og_missing = [k for k in ["og:title", "og:description"] if not parser.og_tags.get(k)]
        if len(og_missing) == 2:
            self._add_finding(
                "Open Graph Tags Absent", "high", "discoverability", url,
                "og:title and og:description both missing.",
                "Add og:title, og:description, and og:image for AI preview and knowledge graph consensus.",
                "high", "citation", "page", f"no_og:{url}"
            )
        elif og_missing:
            self._add_finding(
                "Incomplete Open Graph Tags", "medium", "discoverability", url,
                f"Missing: {', '.join(og_missing)}.",
                "Complete Open Graph tag set: og:title, og:description, og:image.",
                "medium", "citation", "page", f"partial_og:{url}"
            )

        # hreflang x-default check (root only)
        if url == self.base_url and parser.hreflang_tags:
            has_xdefault = any(t["hreflang"].lower() == "x-default" for t in parser.hreflang_tags)
            if not has_xdefault:
                self._add_finding(
                    "Missing hreflang x-default", "medium", "discoverability", url,
                    f"hreflang alternate tags present ({len(parser.hreflang_tags)}) but no x-default.",
                    "Add <link rel=\"alternate\" hreflang=\"x-default\"> to declare the canonical language fallback.",
                    "medium", "citation", "site", "no_hreflang_xdefault"
                )

    def check_freshness(self, url: str, data: Dict[str, Any]):
        import datetime as _dt
        parser = data["parser"]
        headers = data["headers"]
        nodes = self._get_schema(data)
        words = parser.get_word_count()
        is_content_page = words > 150 or parser.heading_counts.get("h1", 0) > 0

        has_temporal = False
        temporal_value: Optional[str] = None
        has_sameas = False
        has_org = False
        has_disambig = False

        for node in nodes:
            t = str(node.get("@type", "")).lower()
            if any(x in t for x in {"organization", "brand", "corporation", "localbusiness"}):
                has_org = True
                same = node.get("sameAs")
                # sameAs must contain at least one external URL
                if same and any(
                    urllib.parse.urlparse(s).netloc != self.parsed.netloc
                    for s in (same if isinstance(same, list) else [same])
                ):
                    has_sameas = True
                if node.get("disambiguatingDescription"):
                    has_disambig = True
            dm = node.get("dateModified") or node.get("datePublished")
            if dm:
                has_temporal = True
                temporal_value = str(dm)

        if has_org and not has_sameas:
            self._add_finding(
                "Missing sameAs Knowledge Graph Anchors", "medium", "discoverability", url,
                "Organization/Brand JSON-LD lacks sameAs links to external authority nodes.",
                "Add sameAs links to Wikidata, Wikipedia, LinkedIn, or Crunchbase for this brand.",
                "medium", "citation", "brand", f"no_sameas:{url}"
            )
        if has_org and not has_disambig:
            self._add_finding(
                "Missing disambiguatingDescription", "medium", "discoverability", url,
                "Brand entity JSON-LD lacks disambiguatingDescription.",
                "Add a 1–2 sentence disambiguatingDescription to prevent AI homonym conflation.",
                "medium", "citation", "brand", f"no_disambig:{url}"
            )

        lm_header = headers.get("last-modified", "")
        if not has_temporal and not lm_header and is_content_page:
            self._add_finding(
                "Missing Temporal Freshness Signals", "medium", "discoverability", url,
                "No dateModified/datePublished in JSON-LD and no Last-Modified HTTP header on a content page.",
                "Add dateModified in JSON-LD and configure Last-Modified HTTP header.",
                "medium", "citation", "page", f"no_temporal:{url}"
            )

        # Stale date check: flag if date is present but > 365 days old on a page with price signals
        if temporal_value or lm_header:
            import re as _re
            text = parser.get_plain_text()
            has_price = bool(_re.search(r'[$€£₹]\s*\d', text))
            date_str = temporal_value or lm_header
            try:
                date_str_clean = date_str[:10]  # take YYYY-MM-DD prefix
                page_date = _dt.date.fromisoformat(date_str_clean)
                age_days = (_dt.date.today() - page_date).days
                if age_days > 365 and has_price:
                    self._add_finding(
                        "Stale Date on Commerce Page", "medium", "discoverability", url,
                        f"Date signal '{date_str_clean}' is {age_days} days old; price/commerce signals present.",
                        "Update dateModified when product details change; AI assistants may cite outdated pricing.",
                        "medium", "citation", "page", f"stale_date:{url}"
                    )
            except (ValueError, TypeError):
                pass  # unparseable date; skip stale check

        raw_text = parser.get_plain_text()
        import re as _re
        c_match = _re.search(r'(?:©|&copy;|copyright)\s*(?:20\d\d\s*[-–—]\s*)?(20\d\d)', raw_text, _re.IGNORECASE)
        if c_match:
            c_year = int(c_match.group(1))
            current_year = datetime.datetime.now(datetime.timezone.utc).year
            if c_year < current_year - 2:
                self._add_finding(
                    "Stale Copyright Year in Footer",
                    "medium", "discoverability", url,
                    f"Footer copyright year is {c_year}, which is {current_year - c_year} years behind current year ({current_year}). Stale copyright signals an unmaintained or abandoned domain to AI crawlers.",
                    f"Update copyright year in page templates to {current_year} or implement a dynamic year snippet.",
                    "medium", "citation", "page", f"stale_copyright:{url}"
                )

    def check_engagement(self, url: str, data: Dict[str, Any]):
        import re as _re
        parser = data["parser"]
        words = parser.get_word_count()
        is_content_page = words > 200

        if not is_content_page:
            return  # skip engagement checks on thin/nav pages

        first_200_words = " ".join(parser.get_plain_text().split()[:200])
        if parser.heading_counts.get("h1", 0) > 0 and len(first_200_words.split()) >= 40:
            has_definition = any(term in first_200_words.lower() for term in [
                "is a", "is the", "provides", "offers", "helps", "platform", "solution", "tool", "service", "designed to", "leading"
            ])
            if not has_definition:
                self._add_finding(
                    "Weak Lead Answer Density", "medium", "engagement", url,
                    "Primary <h1> is not followed by an immediate value proposition or entity definition in the first 200 words. AI answer engines (AEO) prioritize front-loaded definitions for direct answers.",
                    "Add a clear, front-loaded 30-50 word summary sentence directly below the <h1> defining what the brand or page provides.",
                    "medium", "engagement", "page", f"lead_answer_density:{url}"
                )

        if words > 400 and parser.breaker_count < 2:
            self._add_finding(
                "Low Content Scannability — Missing Structural Breakers", "medium", "engagement", url,
                f"Page contains {words} words but only {parser.breaker_count} structural breaker element(s) (lists, tables, blockquotes). LLMs cite structured bullet lists and comparison tables with 3x higher frequency than uninterrupted text walls.",
                "Incorporate bulleted lists (<ul>/<ol>) or comparison tables to structure key data points for AI extraction.",
                "medium", "engagement", "page", f"low_scannability:{url}"
            )

        # 1. Deep semantic anchors — check count, not specific names
        id_count = len(parser.element_ids)
        if id_count < 2:
            self._add_finding(
                "Sparse Section Anchors", "medium", "engagement", url,
                f"Only {id_count} element(s) with id attributes on a content page ({words} words). "
                "Deep-linking to specific facts is not possible.",
                "Add id attributes to major content sections to enable AI deep-link citations.",
                "medium", "engagement", "page", f"sparse_anchors:{url}"
            )

        # 2. Referrer readiness — pattern-driven, not brand-name-specific
        scripts_combined = " ".join(parser.inline_scripts).lower()
        has_referrer_pattern = any(p in scripts_combined for p in REFERRER_PATTERNS)
        if not has_referrer_pattern and self._get_schema(data):
            # only flag if page has structured data (implies AI referral is plausible)
            self._add_finding(
                "No Referrer-Awareness in Page Scripts", "medium", "engagement", url,
                "Inline scripts contain no document.referrer or query-string parsing pattern. "
                "AI-referred visitors cannot be detected or contextually welcomed.",
                "Add referrer detection (document.referrer or UTM params) to tailor landing experience for AI traffic.",
                "medium", "engagement", "page", f"no_referrer:{url}"
            )

        # 3. Conversion path visibility — DOM-position proxy
        total_blocks = max(parser.block_element_count, 1)
        first_cta: Optional[Tuple[str, int]] = None
        for elem_text, pos in parser.transactional_elements:
            if any(v in elem_text.lower() for v in TRANSACTIONAL_VERBS):
                first_cta = (elem_text, pos)
                break
        # also scan inline text of <a>/<button> captured in text_chunks
        if first_cta is None:
            text = parser.get_plain_text().lower()
            if not any(v in text for v in TRANSACTIONAL_VERBS):
                self._add_finding(
                    "No Transactional CTA Detected", "medium", "engagement", url,
                    "No button or link with purchase/contact/download intent text found.",
                    "Add a clear call-to-action above the fold on product/service pages.",
                    "medium", "engagement", "page", f"no_cta:{url}"
                )
        elif first_cta[1] / total_blocks > 0.6:
            self._add_finding(
                "Conversion CTA Below Page Fold", "medium", "engagement", url,
                f"First transactional element ('{first_cta[0][:40]}') appears at DOM depth "
                f"{first_cta[1]}/{total_blocks} ({int(first_cta[1]/total_blocks*100)}% down).",
                "Move primary CTA higher in the document so AI-referred visitors encounter it immediately.",
                "medium", "engagement", "page", f"late_cta:{url}"
            )

        # 4. noscript divergence
        noscript_text = parser.get_noscript_text()
        if noscript_text:
            main_words = set(parser.get_plain_text().lower().split())
            noscript_words = set(noscript_text.lower().split())
            if noscript_words and main_words:
                overlap = len(main_words & noscript_words) / len(noscript_words)
                if overlap < 0.5:
                    self._add_finding(
                        "noscript Content Diverges from Main Page", "medium", "engagement", url,
                        f"noscript block shares only {int(overlap*100)}% word overlap with main body. "
                        "Non-JS crawlers (and some AI agents) see a materially different page.",
                        "Ensure noscript fallback reflects key content; avoid misleading bots with placeholder text.",
                        "medium", "engagement", "page", f"noscript_diverge:{url}"
                    )

    def post_crawl_taxonomy_audit(self):
        prefix_to_cats: Dict[str, Set[str]] = {}
        pages_with_schema = 0
        for url, data in self.page_data.items():
            nodes = self._get_schema(data)
            if not nodes:
                continue
            pages_with_schema += 1
            path = urllib.parse.urlparse(url).path
            seg = [s for s in path.split("/") if s]
            prefix = seg[0] if seg else "(root)"

            for node in nodes:
                t = str(node.get("@type", "")).lower()
                if "product" in t or "article" in t or "service" in t:
                    cat = node.get("category") or node.get("additionalType") or node.get("@type")
                    if cat:
                        prefix_to_cats.setdefault(prefix, set()).add(str(cat).lower())

        if pages_with_schema < 3:
            return  # insufficient data; skip

        for prefix, cats in prefix_to_cats.items():
            if len(cats) > 1:
                self._add_finding(
                    "Cross-Category Semantic Bleed", "medium", "engagement", self.base_url,
                    f"URL prefix '/{prefix}/' maps to multiple schema categories: {', '.join(sorted(cats))}.",
                    "Isolate distinct product/content lines under separate URL namespaces to prevent AI entity conflation.",
                    "medium", "engagement", "site", f"taxonomy_bleed:{prefix}"
                )

    def audit_sitemap(self):
        sitemap_url = f"{self.parsed.scheme}://{self.parsed.netloc}/sitemap.xml"
        status, _, content = self.fetch_url(sitemap_url)
        if status != 200 or not content:
            self._add_finding(
                "Sitemap Absent or Unreachable", "medium", "discoverability", sitemap_url,
                f"GET {sitemap_url} returned HTTP {status or 'Unreachable'}.",
                "Publish /sitemap.xml with <lastmod> on all URLs and reference it in robots.txt.",
                "medium", "citation", "site", "sitemap_missing"
            )
            return

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            self._add_finding(
                "Sitemap XML Malformed", "medium", "discoverability", sitemap_url,
                f"XML parse error: {e}. Crawlers and AI indexers may fail to process it.",
                "Fix sitemap XML syntax. Validate at sitemap.org before deploying.",
                "medium", "citation", "site", "sitemap_malformed"
            )
            return

        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        tag = root.tag.lower()

        if "sitemapindex" in tag:
            # recurse one level: fetch and parse child sitemaps
            child_locs = [
                el.findtext("ns:loc", namespaces=ns) or el.findtext("loc", default="")
                for el in (root.findall(".//ns:sitemap", ns) or root.findall(".//sitemap"))
            ]
            items: List[Any] = []
            for child_url in child_locs[:5]:  # limit to first 5 child sitemaps
                if not child_url or self._overtime():
                    break
                _, _, child_content = self.fetch_url(child_url.strip())
                if child_content:
                    try:
                        child_root = ET.fromstring(child_content)
                        items.extend(
                            child_root.findall(".//ns:url", ns) or child_root.findall(".//url")
                        )
                    except ET.ParseError:
                        pass  # log but continue
        else:
            items = root.findall(".//ns:url", ns) or root.findall(".//url")

        if not items:
            self._add_finding(
                "Sitemap Contains No URLs", "medium", "discoverability", sitemap_url,
                "Sitemap parsed successfully but contains zero <url> entries.",
                "Ensure sitemap lists all indexable pages with <loc> and <lastmod>.",
                "medium", "citation", "site", "sitemap_empty"
            )
            return

        missing = sum(
            1 for el in items
            if el.find("ns:lastmod", ns) is None and el.find("lastmod") is None
        )
        if missing / len(items) > 0.5:
            self._add_finding(
                "Sitemap Lacks lastmod on Majority of URLs", "medium", "discoverability", sitemap_url,
                f"{missing}/{len(items)} entries missing <lastmod>.",
                "Add ISO 8601 <lastmod> to every sitemap entry to signal content freshness to AI crawlers.",
                "medium", "citation", "site", "sitemap_no_lastmod"
            )

    def audit_legacy_urls(self):
        crawled_paths = [
            urllib.parse.urlparse(u).path.rstrip("/")
            for u in list(self.page_data.keys())
            if urllib.parse.urlparse(u).path not in ("", "/")
        ]
        if len(crawled_paths) < 3:
            return  # insufficient pattern basis; skip

        # Infer archival variants from observed path structure
        probes: Set[str] = set()
        for path in crawled_paths[:4]:
            segments = [s for s in path.split("/") if s]
            if not segments:
                continue
            # Variant A: append archival suffix to the last non-numeric segment
            last_seg = segments[-1]
            if not last_seg.isdigit():
                probes.add("/" + "/".join(segments[:-1] + [last_seg + "-old"]))
            # Variant B: prepend /archive to the path
            probes.add("/archive" + path)

        stale: List[str] = []
        for probe in list(probes)[:6]:  # cap probes to avoid budget bleed
            if self._overtime():
                break
            test = f"{self.parsed.scheme}://{self.parsed.netloc}{probe}"
            st, _, _ = self.fetch_url(test)
            if st == 200:
                stale.append(probe)

        if stale:
            self._add_finding(
                "Inferred Legacy URLs Return HTTP 200", "medium", "discoverability", self.base_url,
                f"Probed retired-URL variants returned 200: {', '.join(stale[:4])}.",
                "Return HTTP 301 (redirect to current canonical) or 410 Gone for discontinued pages "
                "to prevent AI assistants from citing stale content.",
                "medium", "citation", "site", "legacy_200"
            )

    def check_entity_trust(self):
        """Site-wide entity identity and trust checks (EntityTrustChecker)."""
        if not self.page_data:
            return

        AUTHORITY_DOMAINS = {
            "wikidata.org", "wikipedia.org", "linkedin.com", "crunchbase.com",
            "bloomberg.com", "forbes.com", "github.com", "youtube.com",
            "twitter.com", "x.com", "facebook.com", "instagram.com",
        }
        ORG_TYPES = {"organization", "corporation", "brand", "localbusiness", "nonprofit"}

        # ── Collect all Organization/Brand JSON-LD nodes across pages ──
        org_nodes: List[Dict[str, Any]] = []
        for url, data in self.page_data.items():
            for node in self._get_schema(data):
                t = str(node.get("@type", "")).lower()
                if t in ORG_TYPES:
                    org_nodes.append({"url": url, "node": node})

        # ── 1. Organization identity unclear ──
        has_org_jsonld = bool(org_nodes)
        has_visible_identity = any(
            data.get("word_count", 0) > 50
            for data in self.page_data.values()
        )
        if has_visible_identity and not has_org_jsonld:
            self._add_finding(
                "Machine-Readable Organization Identity Missing",
                "high", "entity_identity", self.base_url,
                "Visible site content present but no Organization, Corporation, Brand, or LocalBusiness JSON-LD found across any crawled page.",
                "Add Organization JSON-LD with name, url, logo, sameAs, and disambiguatingDescription to the homepage.",
                "high", "citation", "site", "et_machine_identity_gap"
            )

        if org_nodes:
            # ── 2. sameAs authority validation ──
            any_authority_sameas = False
            for entry in org_nodes:
                sameas = entry["node"].get("sameAs") or []
                if isinstance(sameas, str):
                    sameas = [sameas]
                for link in sameas:
                    try:
                        host = urllib.parse.urlparse(link).netloc.lower().lstrip("www.")
                        if any(auth in host for auth in AUTHORITY_DOMAINS):
                            any_authority_sameas = True
                            break
                    except Exception:
                        pass
                if any_authority_sameas:
                    break
            if not any_authority_sameas:
                self._add_finding(
                    "sameAs Links Missing or Pointing to Non-Authority Domains",
                    "medium", "entity_identity", self.base_url,
                    "Organization JSON-LD found but sameAs field is absent or points to no recognized authority domain (Wikidata, Wikipedia, LinkedIn, Crunchbase, etc.).",
                    "Add sameAs links in Organization JSON-LD to Wikidata, Wikipedia, and LinkedIn profiles. Authority-domain links are weighted heavily by AI knowledge graph ingestion.",
                    "medium", "citation", "brand", "et_sameas_authority"
                )

            # ── 3. disambiguatingDescription ──
            has_disambig = any(
                entry["node"].get("disambiguatingDescription")
                for entry in org_nodes
            )
            if not has_disambig:
                self._add_finding(
                    "Organization Lacks disambiguatingDescription",
                    "medium", "entity_identity", self.base_url,
                    "Organization/Brand JSON-LD found but disambiguatingDescription field is absent. AI models use this field to distinguish similarly-named entities.",
                    "Add disambiguatingDescription to Organization JSON-LD (e.g. \"Acme Inc. is a B2B SaaS company focused on supply-chain analytics, distinct from Acme Corp. the hardware retailer.\").",
                    "medium", "citation", "brand", "et_disambig_description"
                )

            # ── 4. @id stability across pages ──
            entity_ids: List[str] = []
            for entry in org_nodes:
                eid = entry["node"].get("@id", "")
                if eid:
                    entity_ids.append(eid)
            unique_ids = set(entity_ids)
            if len(unique_ids) > 1:
                self._add_finding(
                    "Unstable Entity @id Across Pages",
                    "high", "entity_identity", self.base_url,
                    f"Organization JSON-LD uses {len(unique_ids)} distinct @id values across crawled pages: {', '.join(sorted(unique_ids)[:3])}. AI knowledge graphs treat each @id as a separate entity.",
                    "Standardize @id to a single canonical URL (e.g. https://example.com/#organization) across all Organization JSON-LD blocks sitewide.",
                    "high", "citation", "site", "et_unstable_entity_id"
                )

            # ── 5. Cross-page identity name drift ──
            names: List[str] = []
            for entry in org_nodes:
                name = str(entry["node"].get("name", "")).strip().lower()
                if name:
                    names.append(name)
            unique_names = set(names)
            if len(unique_names) > 1:
                self._add_finding(
                    "Inconsistent Brand Name in Organization JSON-LD",
                    "medium", "entity_identity", self.base_url,
                    f"Organization JSON-LD name field varies across pages: {', '.join(sorted(unique_names)[:4])}. Inconsistent naming causes entity conflation in AI knowledge graphs.",
                    "Normalize the name field in all Organization JSON-LD blocks to a single canonical brand name matching your registered trademark.",
                    "medium", "citation", "site", "et_name_drift"
                )

            # ── 7. Canonical vs Structured Data URL drift ──
            for entry in org_nodes:
                ent_url = entry["node"].get("url")
                if ent_url and isinstance(ent_url, str):
                    norm_ent_url = self._normalize(ent_url)
                    p_data = self.page_data.get(entry["url"], {})
                    canon = p_data.get("canonical") or (p_data.get("parser").canonical if p_data.get("parser") else "")
                    if canon:
                        norm_canon = self._normalize(canon)
                        if norm_ent_url != norm_canon and urllib.parse.urlparse(norm_ent_url).netloc == urllib.parse.urlparse(norm_canon).netloc:
                            self._add_finding(
                                "Structured Data URL Drifts from Canonical",
                                "medium", "entity_identity", entry["url"],
                                f"Organization JSON-LD url '{ent_url}' does not match page canonical URL '{canon}'. Discrepancies cause knowledge graphs to fragment entity authority.",
                                "Align the url property in Organization JSON-LD to match the page canonical URL.",
                                "medium", "citation", "page", f"et_canon_drift:{entry['url']}"
                            )
                            break

        # ── 6. Offering identity check ──
        PRODUCT_TYPES = {"product", "service", "softwareapplication", "course", "event", "offer"}
        for url, data in self.page_data.items():
            if self._overtime():
                break
            path = urllib.parse.urlparse(url).path.lower()
            is_offering_page = any(seg in path for seg in ("/product", "/service", "/plan", "/pricing", "/solution", "/shop", "/buy"))
            has_commerce_text = any(
                phrase in (data.get("html", "") or "").lower()
                for phrase in ["add to cart", "buy now", "add to bag", "purchase", "$", "€", "£"]
            )
            if is_offering_page or has_commerce_text:
                schema_nodes = self._get_schema(data)
                has_product_schema = self._has_type(schema_nodes, PRODUCT_TYPES)
                if not has_product_schema:
                    self._add_finding(
                        "Offering Page Missing Product/Service JSON-LD",
                        "medium", "entity_identity", url,
                        f"Page appears to describe an offering (URL: {url}) but no Product, Service, or Offer JSON-LD found.",
                        "Add Product or Service JSON-LD with name, description, category, and offers (including price and priceCurrency) to each offering page.",
                        "medium", "citation", "page", f"et_offering_identity::{url}"
                    )

        has_relationships = any(
            any(rel in entry["node"] for rel in ["contactPoint", "founder", "parentOrganization", "subOrganization", "department", "hasOfferCatalog", "brand", "makesOffer"])
            for entry in org_nodes
        )
        if org_nodes and not has_relationships:
            self._add_finding(
                "Organization Schema Lacks Entity Relationships",
                "medium", "entity_identity", self.base_url,
                "Organization JSON-LD exists in isolation without nested or linked relationships (contactPoint, founder, brand, department, or offerCatalog). AI knowledge graphs prioritize interconnected entity graphs over isolated nodes.",
                "Enrich Organization JSON-LD with contactPoint, founder, or brand entity relationships.",
                "medium", "citation", "brand", "et_missing_relationships"
            )

        all_links = set()
        for p in self.page_data.values():
            if p.get("parser"):
                all_links.update(p["parser"].links)
        has_legal = any(
            any(w in l.lower() for w in ["privacy", "terms", "legal", "tos", "disclaimer", "cookie-policy", "impressum"])
            for l in all_links
        )
        if not has_legal and self.page_data:
            self._add_finding(
                "No Privacy Policy or Terms of Service Linked",
                "medium", "entity_identity", self.base_url,
                "No links to privacy policy, terms of service, or legal pages detected across crawled pages. AI search engines evaluate legal transparency as a foundational domain credibility signal.",
                "Add clear, crawlable links to Privacy Policy and Terms of Service in the global site footer.",
                "medium", "citation", "site", "missing_legal_pages"
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
        self.check_entity_trust()
        self._emit_proactive_suggestions()

        return self._compile_report()

    def _emit_proactive_suggestions(self):
        """Proactive recommendations even where no explicit defect was found."""
        # Check for SpeakableSpecification across all pages (proactive, not a defect)
        has_speakable = any(
            self._has_type(self._get_schema(d), {"speakablespecification"})
            for d in self.page_data.values()
        )
        if not has_speakable and self.page_data:
            self._add_finding(
                "SpeakableSpecification Not Present", "medium", "discoverability", self.base_url,
                "No SpeakableSpecification markup detected across crawled pages.",
                "Add SpeakableSpecification with cssSelector targeting key content blocks "
                "to guide voice assistants and AI answer extraction.",
                "medium", "citation", "site", "no_speakable_proactive"
            )

        # Cross-web corroboration gap: if no sameAs found anywhere
        any_sameas = False
        for d in self.page_data.values():
            for node in self._get_schema(d):
                if node.get("sameAs"):
                    any_sameas = True
                    break
            if any_sameas:
                break
        if not any_sameas and self.page_data:
            self._add_finding(
                "Brand Lacks Cross-Web Entity Anchoring", "medium", "discoverability", self.base_url,
                "No sameAs links to external authority sources found across any crawled page.",
                "Establish brand presence on Wikidata, Wikipedia, and industry directories; "
                "add sameAs links in Organization JSON-LD to those profiles.",
                "medium", "citation", "brand", "no_crossweb_corroboration"
            )

    def _apply_severity_boosting(self):
        """Issue-family correlation: upgrade medium→high when 2+ skills flag the same URL.
        Implements the teammate's evidence-correlator corroboration logic inline."""
        SCHEMA_FAMILY = {"no_jsonld", "malformed_jsonld", "product_schema_missing",
                         "et_machine_identity_gap", "et_offering_identity"}
        FRESHNESS_FAMILY = {"no_date_marker", "stale_date", "sitemap_no_lastmod"}

        # Group findings by URL
        by_url: Dict[str, List[Dict[str, Any]]] = {}
        for f in self.findings:
            by_url.setdefault(f.get("url", ""), []).append(f)

        for url, findings in by_url.items():
            check_ids = {f.get("suggested_action", {}).get("scope", "") + f.get("title", "") for f in findings}
            schema_hits = sum(1 for f in findings if any(fam in f.get("id", "") + f.get("title", "").lower() for fam in ["json-ld", "schema", "structured data", "entity"]))
            freshness_hits = sum(1 for f in findings if any(fam in f.get("title", "").lower() for fam in ["date", "freshness", "lastmod", "stale"]))

            # Corroboration rule: 2+ independent signals on same URL → upgrade medium to high
            if schema_hits >= 2 or freshness_hits >= 2:
                for f in findings:
                    if f["severity"] == "medium":
                        if schema_hits >= 2 and any(kw in f.get("title", "").lower() for kw in ["json-ld", "schema", "structured data"]):
                            f["severity"] = "high"
                        elif freshness_hits >= 2 and any(kw in f.get("title", "").lower() for kw in ["date", "freshness", "lastmod", "stale"]):
                            f["severity"] = "high"

    def _compile_report(self) -> Dict[str, Any]:
        self._apply_severity_boosting()
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        self.findings.sort(key=lambda x: order.get(x["severity"], 4))

        score = 100
        for f in self.findings:
            sev = f.get("severity", "medium")
            if sev == "critical":
                score -= 25
            elif sev == "high":
                score -= 10
            elif sev == "medium":
                score -= 3
        score = max(0, min(100, score))

        verdicts = {
            "crawl_render": "pass",
            "entity_trust": "pass",
            "freshness": "pass",
            "engagement": "pass"
        }
        for f in self.findings:
            cat = (f.get("category", "") + " " + f.get("id", "")).lower()
            sev = f.get("severity", "medium")
            phase_key = "crawl_render"
            if "entity" in cat:
                phase_key = "entity_trust"
            elif "fresh" in cat:
                phase_key = "freshness"
            elif "engage" in cat:
                phase_key = "engagement"

            if sev == "critical":
                verdicts[phase_key] = "fail"
            elif sev == "high" and verdicts[phase_key] != "fail":
                verdicts[phase_key] = "warn"

        critical_count = sum(1 for f in self.findings if f["severity"] == "critical")
        high_count = sum(1 for f in self.findings if f["severity"] == "high")
        if critical_count > 0:
            headline = f"{self.domain} has {critical_count} critical visibility barrier(s) blocking automated AI crawlers and indexers."
        elif high_count >= 3:
            headline = f"{self.domain} has significant AI readiness gaps across discoverability and entity trust requiring remediation."
        elif high_count > 0:
            headline = f"{self.domain} is partially AI-ready but {high_count} high-severity issue(s) limit citation probability."
        else:
            headline = f"{self.domain} demonstrates solid AI readiness with {len(self.findings)} optimization opportunities."

        top_priority = self.findings[0]["suggested_action"]["summary"] if self.findings else "Site is fully AI-ready."

        summary = {
            "ai_readiness_score": score,
            "headline": headline,
            "top_priority": top_priority,
            "total_findings": len(self.findings),
            "critical": critical_count,
            "high": high_count,
            "medium": sum(1 for f in self.findings if f["severity"] == "medium"),
            "phase_verdicts": verdicts
        }

        return {
            "site": self.domain,
            "audited_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "crawl_meta": {
                "pages_crawled": len(self.page_data),
                "pages_errored": len(self.crawl_errors),
                "errors": self.crawl_errors
            },
            "summary": summary,
            "findings": self.findings
        }


def main():
    p = argparse.ArgumentParser(description="Brand AI-Readiness Audit Engine v3.0")
    p.add_argument("--url", required=True)
    p.add_argument("--max-pages", type=int, default=5)
    p.add_argument("--timeout", type=int, default=15, help="Per-request timeout in seconds (default: 15)")
    p.add_argument("--out", help="Output JSON file path")
    args = p.parse_args()

    engine = AuditEngine(base_url=args.url, max_pages=args.max_pages, timeout=args.timeout)
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
