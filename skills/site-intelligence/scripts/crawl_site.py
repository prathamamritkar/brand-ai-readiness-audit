#!/usr/bin/env python3
"""Bounded, read-only website evidence collector.

Standard-library only. Emits a JSON evidence bundle to stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib import robotparser
import urllib.request
import xml.etree.ElementTree as ET


USER_AGENT = "BrandAIReadinessAudit/0.1 (+read-only)"
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_PAGES = 20
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_SECONDS = 120


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid HTTP(S) URL: {raw}")
    path = parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def origin(url: str) -> tuple[str, str]:
    p = urlparse(url)
    return p.scheme, p.netloc


def same_origin(url: str, root_origin: tuple[str, str]) -> bool:
    p = urlparse(url)
    return (p.scheme, p.netloc) == root_origin


def clean_link(base: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    absolute = urljoin(base, href)
    absolute, _ = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))


class PageParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.meta_description = ""
        self.canonical = None
        self.headings: list[dict] = []
        self.links: list[str] = []
        self.jsonld: list[str] = []
        self.text_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._current_heading: tuple[str, list[str]] | None = None
        self._in_jsonld = False
        self._jsonld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        attrs_dict = {k.lower(): v for k, v in attrs if k}

        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

        if tag == "title":
            self._in_title = True

        if tag == "meta" and attrs_dict.get("name", "").lower() == "description":
            self.meta_description = (attrs_dict.get("content") or "").strip()

        if tag == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            href = attrs_dict.get("href")
            if href:
                self.canonical = clean_link(self.base_url, href)

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._skip_depth == 0:
            self._current_heading = (tag, [])

        if tag == "a" and self._skip_depth == 0:
            href = attrs_dict.get("href")
            link = clean_link(self.base_url, href) if href else None
            if link:
                self.links.append(link)

        if tag == "script" and attrs_dict.get("type", "").lower() in {
            "application/ld+json", "application/json+ld"
        }:
            self._in_jsonld = True
            self._jsonld_parts = []

        self._tag_stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._current_heading:
            heading_tag, parts = self._current_heading
            text = " ".join(" ".join(parts).split())
            if text:
                self.headings.append({"level": int(heading_tag[1]), "text": text})
            self._current_heading = None

        if tag == "title":
            self._in_title = False

        if tag == "script" and self._in_jsonld:
            payload = "".join(self._jsonld_parts).strip()
            if payload:
                self.jsonld.append(payload)
            self._in_jsonld = False
            self._jsonld_parts = []

        if self._skip_depth and tag in self.SKIP_TAGS:
            self._skip_depth -= 1

        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_parts.append(data)
            return

        if self._in_title:
            self.title += data

        if self._skip_depth == 0:
            normalized = " ".join(data.split())
            if normalized:
                self.text_parts.append(normalized)
                if self._current_heading:
                    self._current_heading[1].append(normalized)

    def evidence(self):
        text = " ".join(self.text_parts)
        return {
            "title": " ".join(self.title.split()),
            "meta_description": self.meta_description,
            "canonical": self.canonical,
            "headings": self.headings,
            "visible_text_chars": len(text),
            "links": sorted(set(self.links)),
            "jsonld_blocks": self.jsonld,
        }


def fetch(url: str, timeout: int, max_bytes: int):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    started = time.monotonic()
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            final_url = response.geturl()
            status = getattr(response, "status", 200)
            data = response.read(max_bytes + 1)
            truncated = len(data) > max_bytes
            if truncated:
                data = data[:max_bytes]
            charset = response.headers.get_content_charset() or "utf-8"
            try:
                text = data.decode(charset, errors="replace")
            except LookupError:
                text = data.decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": status,
                "final_url": final_url,
                "content_type": content_type,
                "bytes": len(data),
                "truncated": truncated,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "text": text,
                "error": None,
            }
    except HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "final_url": url,
            "content_type": exc.headers.get_content_type() if exc.headers else None,
            "bytes": 0,
            "truncated": False,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "text": "",
            "error": f"HTTPError: {exc.code}",
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "status": None,
            "final_url": url,
            "content_type": None,
            "bytes": 0,
            "truncated": False,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_robots(base: str, timeout: int):
    robots_url = urljoin(base, "/robots.txt")
    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=timeout) as response:
            text = response.read(256 * 1024).decode("utf-8", errors="replace")
        parser.parse(text.splitlines())
        sitemaps = []
        for line in text.splitlines():
            if line.lower().startswith("sitemap:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    sitemaps.append(value)
        return {
            "url": robots_url,
            "available": True,
            "allowed_for_user_agent": parser.can_fetch(USER_AGENT, base),
            "sitemaps": sitemaps,
            "_parser": parser,
        }
    except Exception as exc:
        # Absence/unavailability of robots.txt is recorded; it is not treated as permission to bypass an explicit policy.
        return {
            "url": robots_url,
            "available": False,
            "allowed_for_user_agent": True,
            "sitemaps": [],
            "error": f"{type(exc).__name__}: {exc}",
            "_parser": parser,
        }


def sitemap_urls(url: str, timeout: int, limit: int = 200):
    result = []
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*;q=0.5"})
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024)
        root = ET.fromstring(raw)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [el.text.strip() for el in root.findall(".//sm:url/sm:loc", ns) if el.text]
        if not locs:
            # Sitemap index
            locs = [el.text.strip() for el in root.findall(".//sm:sitemap/sm:loc", ns) if el.text]
            for child in locs[:10]:
                result.extend(sitemap_urls(child, timeout, max(0, limit - len(result))))
                if len(result) >= limit:
                    break
            return result[:limit]
        return locs[:limit]
    except Exception:
        return result


def crawl(start_url: str, max_pages: int, max_depth: int, max_bytes: int, max_seconds: int, timeout: int):
    started = time.monotonic()
    start_url = normalize_url(start_url)
    root_origin = origin(start_url)

    robots = load_robots(start_url, timeout)
    parser = robots["_parser"]
    del robots["_parser"]

    queue = deque([(start_url, 0)])
    seen = {start_url}
    pages = []

    while queue and len(pages) < max_pages and (time.monotonic() - started) < max_seconds:
        url, depth = queue.popleft()

        if not same_origin(url, root_origin):
            continue

        if not parser.can_fetch(USER_AGENT, url):
            pages.append({
                "url": url,
                "depth": depth,
                "fetch": {"ok": False, "error": "blocked_by_robots.txt"},
                "evidence": None,
            })
            continue

        result = fetch(url, timeout, max_bytes)
        page = {
            "url": url,
            "depth": depth,
            "fetch": {k: v for k, v in result.items() if k != "text"},
            "evidence": None,
        }

        content_type = result.get("content_type") or ""
        if result["ok"] and "html" in content_type:
            try:
                parser_obj = PageParser(result["final_url"])
                parser_obj.feed(result["text"])
                evidence = parser_obj.evidence()
                page["evidence"] = evidence

                if depth < max_depth:
                    for link in evidence["links"]:
                        if same_origin(link, root_origin) and link not in seen:
                            seen.add(link)
                            queue.append((link, depth + 1))
            except Exception as exc:
                page["parse_error"] = f"{type(exc).__name__}: {exc}"

        pages.append(page)

    sitemap_candidates = list(robots.get("sitemaps", []))
    sitemap_candidates.append(urljoin(start_url, "/sitemap.xml"))
    sitemap_found = []
    for sitemap in dict.fromkeys(sitemap_candidates):
        if same_origin(sitemap, root_origin):
            urls = sitemap_urls(sitemap, timeout)
            sitemap_found.extend([u for u in urls if same_origin(u, root_origin)])

    return {
        "schema_version": "site-evidence/v0.1",
        "site": {
            "input_url": start_url,
            "origin": f"{root_origin[0]}://{root_origin[1]}",
        },
        "crawl": {
            "started_at_unix": time.time(),
            "duration_ms": round((time.monotonic() - started) * 1000),
            "max_pages": max_pages,
            "max_depth": max_depth,
            "max_bytes_per_response": max_bytes,
            "max_seconds": max_seconds,
            "pages_crawled": len(pages),
        },
        "robots": robots,
        "sitemap": {
            "candidates": list(dict.fromkeys(sitemap_candidates)),
            "urls_discovered": list(dict.fromkeys(sitemap_found))[:200],
        },
        "pages": pages,
    }


def main():
    ap = argparse.ArgumentParser(description="Collect bounded website evidence.")
    ap.add_argument("url")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    ap.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    ap.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    ap.add_argument("--max-seconds", type=int, default=DEFAULT_MAX_SECONDS)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = ap.parse_args()

    if min(args.max_pages, args.max_depth, args.max_bytes, args.max_seconds, args.timeout) <= 0:
        ap.error("All numeric limits must be positive.")

    try:
        bundle = crawl(
            args.url,
            args.max_pages,
            args.max_depth,
            args.max_bytes,
            args.max_seconds,
            args.timeout,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2

    print(json.dumps(bundle, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
