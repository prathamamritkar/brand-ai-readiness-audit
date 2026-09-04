#!/usr/bin/env python3
"""Bounded, read-only website evidence collector.

Standard-library only. Emits a JSON evidence bundle to stdout.
"""

from __future__ import annotations

import argparse
import heapq
import json
import re
import sys
import time
from html.parser import HTMLParser
from urllib import robotparser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urldefrag, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


USER_AGENT = "BrandAIReadinessAudit/0.2 (+read-only)"

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_PAGES = 20
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_SECONDS = 120
DEFAULT_MAX_TEXT_CHARS = 50_000
DEFAULT_SITEMAP_LIMIT = 200

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "dclid",
    "fbclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
}

NON_HTML_EXTENSIONS = {
    ".7z",
    ".avi",
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpg",
    ".jpeg",
    ".mov",
    ".mp3",
    ".mp4",
    ".png",
    ".ppt",
    ".pptx",
    ".pdf",
    ".svg",
    ".tar",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}

PAGE_TYPE_RULES = {
    "about": {"about"},
    "contact": {"contact"},
    "pricing": {"pricing", "plans"},
    "documentation": {"docs", "documentation", "developer", "developers", "api"},
    "blog": {"blog", "news", "articles"},
    "product": {"product", "products"},
    "service": {"service", "services", "solutions"},
    "category": {"category", "categories"},
    "legal": {"legal", "privacy", "terms", "cookies"},
}


def normalize_url(raw: str) -> str:
    raw = raw.strip()

    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw

    parsed = urlparse(raw)

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid HTTP(S) URL: {raw}")

    hostname = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port

    netloc = hostname

    if port and not (
        (parsed.scheme.lower() == "http" and port == 80)
        or (parsed.scheme.lower() == "https" and port == 443)
    ):
        netloc = f"{hostname}:{port}"

    path = re.sub(r"/{2,}", "/", parsed.path or "/")

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]

    query_pairs.sort()

    return urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            path,
            "",
            urlencode(query_pairs),
            "",
        )
    )


def origin(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return parsed.scheme.lower(), parsed.netloc.lower()


def same_origin(url: str, root_origin: tuple[str, str]) -> bool:
    try:
        return origin(url) == root_origin
    except Exception:
        return False


def likely_html_url(url: str) -> bool:
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return False

    return not any(path.endswith(ext) for ext in NON_HTML_EXTENSIONS)


def clean_link(base: str, href: str) -> str | None:
    if not href:
        return None

    href = href.strip()

    if not href or href.startswith(
        ("#", "mailto:", "tel:", "javascript:", "data:")
    ):
        return None

    absolute = urljoin(base, href)
    absolute, _ = urldefrag(absolute)

    try:
        normalized = normalize_url(absolute)
    except ValueError:
        return None

    if not likely_html_url(normalized):
        return None

    return normalized


def classify_page_type(url: str, title: str = "") -> str:
    parsed = urlparse(url)
    segments = {
        segment.lower()
        for segment in parsed.path.split("/")
        if segment
    }

    for page_type, keywords in PAGE_TYPE_RULES.items():
        if segments & keywords:
            return page_type

    lower_title = title.lower()

    for page_type, keywords in PAGE_TYPE_RULES.items():
        if any(keyword in lower_title for keyword in keywords):
            return page_type

    if parsed.path in {"", "/"}:
        return "homepage"

    return "other"


class PageParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)

        self.base_url = base_url
        self.title = ""
        self.meta_description = ""
        self.language = None
        self.canonical = None

        self.headings: list[dict] = []
        self.links: list[str] = []
        self.jsonld: list[str] = []
        self.text_parts: list[str] = []

        self._skip_depth = 0
        self._in_title = False
        self._current_heading: tuple[str, list[str]] | None = None
        self._in_jsonld = False
        self._jsonld_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = {
            key.lower(): value
            for key, value in attrs
            if key
        }

        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

        if tag == "html":
            self.language = (
                attrs_dict.get("lang")
                or attrs_dict.get("xml:lang")
            )

        if tag == "title":
            self._in_title = True

        if (
            tag == "meta"
            and attrs_dict.get("name", "").lower() == "description"
        ):
            self.meta_description = (
                attrs_dict.get("content") or ""
            ).strip()

        if tag == "link":
            rel = attrs_dict.get("rel", "").lower()

            if "canonical" in rel:
                href = attrs_dict.get("href")

                if href:
                    self.canonical = clean_link(
                        self.base_url,
                        href,
                    )

        if (
            tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
            and self._skip_depth == 0
        ):
            self._current_heading = (tag, [])

        if tag == "a" and self._skip_depth == 0:
            href = attrs_dict.get("href")

            if href:
                link = clean_link(
                    self.base_url,
                    href,
                )

                if link:
                    self.links.append(link)

        if (
            tag == "script"
            and attrs_dict.get("type", "").lower()
            in {
                "application/ld+json",
                "application/json+ld",
            }
        ):
            self._in_jsonld = True
            self._jsonld_parts = []

    def handle_endtag(self, tag):
        tag = tag.lower()

        if (
            tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
            and self._current_heading
        ):
            heading_tag, parts = self._current_heading
            text = " ".join(" ".join(parts).split())

            if text:
                self.headings.append(
                    {
                        "level": int(heading_tag[1]),
                        "text": text,
                    }
                )

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

        truncated = len(text) > DEFAULT_MAX_TEXT_CHARS

        if truncated:
            text = text[:DEFAULT_MAX_TEXT_CHARS]

        return {
            "title": " ".join(self.title.split()),
            "language": self.language,
            "meta_description": self.meta_description,
            "canonical": self.canonical,
            "page_type": classify_page_type(
                self.base_url,
                self.title,
            ),
            "headings": self.headings,
            "visible_text": text,
            "visible_text_chars": len(text),
            "visible_text_truncated": truncated,
            "links": sorted(set(self.links)),
            "link_count": len(set(self.links)),
            "jsonld_blocks": self.jsonld,
            "jsonld_block_count": len(self.jsonld),
        }


def fetch(url: str, timeout: int, max_bytes: int):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    )

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

            charset = (
                response.headers.get_content_charset()
                or "utf-8"
            )

            try:
                text = data.decode(
                    charset,
                    errors="replace",
                )
            except LookupError:
                text = data.decode(
                    "utf-8",
                    errors="replace",
                )

            return {
                "ok": True,
                "status": status,
                "final_url": final_url,
                "content_type": content_type,
                "bytes": len(data),
                "truncated": truncated,
                "elapsed_ms": round(
                    (time.monotonic() - started) * 1000
                ),
                "text": text,
                "error": None,
            }

    except HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "final_url": url,
            "content_type": (
                exc.headers.get_content_type()
                if exc.headers
                else None
            ),
            "bytes": 0,
            "truncated": False,
            "elapsed_ms": round(
                (time.monotonic() - started) * 1000
            ),
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
            "elapsed_ms": round(
                (time.monotonic() - started) * 1000
            ),
            "text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_robots(base: str, timeout: int):
    robots_url = urljoin(base, "/robots.txt")

    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)

    try:
        request = Request(
            robots_url,
            headers={"User-Agent": USER_AGENT},
        )

        with urlopen(request, timeout=timeout) as response:
            text = response.read(
                256 * 1024
            ).decode(
                "utf-8",
                errors="replace",
            )

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
            "allowed_for_user_agent": parser.can_fetch(
                USER_AGENT,
                base,
            ),
            "sitemaps": sitemaps,
            "_parser": parser,
            "_failure": False,
        }

    except HTTPError as exc:
        if 400 <= exc.code < 500:
            return {
                "url": robots_url,
                "available": False,
                "allowed_for_user_agent": True,
                "sitemaps": [],
                "error": f"HTTPError: {exc.code}",
                "_parser": parser,
                "_failure": False,
            }

        return {
            "url": robots_url,
            "available": False,
            "allowed_for_user_agent": False,
            "sitemaps": [],
            "error": f"HTTPError: {exc.code}",
            "_parser": parser,
            "_failure": True,
        }

    except (URLError, TimeoutError, OSError) as exc:
        return {
            "url": robots_url,
            "available": False,
            "allowed_for_user_agent": False,
            "sitemaps": [],
            "error": f"{type(exc).__name__}: {exc}",
            "_parser": parser,
            "_failure": True,
        }


def sitemap_urls(
    url: str,
    timeout: int,
    limit: int = DEFAULT_SITEMAP_LIMIT,
):
    result = []

    try:
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/xml,text/xml,*/*;q=0.5",
            },
        )

        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024)

        root = ET.fromstring(raw)

        namespace = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9"
        }

        page_urls = [
            element.text.strip()
            for element in root.findall(
                ".//sm:url/sm:loc",
                namespace,
            )
            if element.text
        ]

        if page_urls:
            return page_urls[:limit]

        sitemap_children = [
            element.text.strip()
            for element in root.findall(
                ".//sm:sitemap/sm:loc",
                namespace,
            )
            if element.text
        ]

        for child in sitemap_children[:10]:
            child_urls = sitemap_urls(
                child,
                timeout,
                max(0, limit - len(result)),
            )

            result.extend(child_urls)

            if len(result) >= limit:
                break

        return result[:limit]

    except Exception:
        return result


def discovery_priority(url: str, depth: int) -> int:
    parsed = urlparse(url)
    path = parsed.path.lower()

    priority = depth * 10

    preferred_terms = (
        "about",
        "contact",
        "pricing",
        "product",
        "products",
        "service",
        "services",
        "solution",
        "solutions",
        "docs",
        "documentation",
        "blog",
    )

    deprioritized_terms = (
        "privacy",
        "terms",
        "login",
        "signin",
        "signup",
        "cookie",
    )

    for term in preferred_terms:
        if term in path:
            priority -= 5

    for term in deprioritized_terms:
        if term in path:
            priority += 8

    return priority


def crawl(
    start_url: str,
    max_pages: int,
    max_depth: int,
    max_bytes: int,
    max_seconds: int,
    timeout: int,
):
    started = time.monotonic()

    start_url = normalize_url(start_url)
    root_origin = origin(start_url)

    robots = load_robots(
        start_url,
        timeout,
    )

    parser = robots.pop("_parser")
    robots_failed = robots.pop("_failure")

    pages = []

    if robots_failed:
        return {
            "schema_version": "site-evidence/v0.2",
            "collector": {
                "name": "site-intelligence",
                "version": "0.2",
            },
            "site": {
                "input_url": start_url,
                "origin": (
                    f"{root_origin[0]}://{root_origin[1]}"
                ),
            },
            "crawl": {
                "started_at_unix": time.time(),
                "duration_ms": round(
                    (time.monotonic() - started) * 1000
                ),
                "max_pages": max_pages,
                "max_depth": max_depth,
                "max_bytes_per_response": max_bytes,
                "max_seconds": max_seconds,
                "pages_crawled": 0,
                "blocked_by_robots_failure": True,
                "page_type_distribution": {},
            },
            "robots": robots,
            "sitemap": {
                "candidates": [],
                "urls_discovered": [],
            },
            "pages": [],
        }

    sitemap_candidates = list(
        robots.get("sitemaps", [])
    )

    sitemap_candidates.append(
        urljoin(start_url, "/sitemap.xml")
    )

    normalized_sitemaps = []

    for sitemap in dict.fromkeys(sitemap_candidates):
        try:
            normalized = normalize_url(sitemap)
        except ValueError:
            continue

        if same_origin(
            normalized,
            root_origin,
        ):
            normalized_sitemaps.append(normalized)

    sitemap_found = []

    for sitemap in normalized_sitemaps:
        urls = sitemap_urls(
            sitemap,
            timeout,
        )

        for candidate in urls:
            try:
                normalized = normalize_url(candidate)
            except ValueError:
                continue

            if (
                same_origin(
                    normalized,
                    root_origin,
                )
                and likely_html_url(normalized)
                and normalized not in sitemap_found
            ):
                sitemap_found.append(normalized)

            if len(sitemap_found) >= DEFAULT_SITEMAP_LIMIT:
                break

        if len(sitemap_found) >= DEFAULT_SITEMAP_LIMIT:
            break

    queue = []
    queued = {start_url}
    seen = set()

    heapq.heappush(
        queue,
        (
            discovery_priority(start_url, 0),
            0,
            start_url,
            "seed",
        ),
    )

    for sitemap_url in sitemap_found:
        if sitemap_url in queued:
            continue

        queued.add(sitemap_url)

        heapq.heappush(
            queue,
            (
                discovery_priority(sitemap_url, 1),
                1,
                sitemap_url,
                "sitemap",
            ),
        )

    while (
        queue
        and len(pages) < max_pages
        and (time.monotonic() - started) < max_seconds
    ):
        _, depth, url, discovered_via = heapq.heappop(queue)

        if url in seen:
            continue

        seen.add(url)

        if not same_origin(url, root_origin):
            continue

        if not likely_html_url(url):
            continue

        if not parser.can_fetch(USER_AGENT, url):
            pages.append(
                {
                    "url": url,
                    "depth": depth,
                    "discovered_via": discovered_via,
                    "fetch": {
                        "ok": False,
                        "error": "blocked_by_robots.txt",
                    },
                    "evidence": None,
                }
            )
            continue

        result = fetch(
            url,
            timeout,
            max_bytes,
        )

        page = {
            "url": url,
            "depth": depth,
            "discovered_via": discovered_via,
            "fetch": {
                key: value
                for key, value in result.items()
                if key != "text"
            },
            "evidence": None,
        }

        content_type = result.get(
            "content_type"
        ) or ""

        if (
            result["ok"]
            and "html" in content_type.lower()
        ):
            try:
                parser_obj = PageParser(
                    result["final_url"]
                )

                parser_obj.feed(
                    result["text"]
                )

                evidence = parser_obj.evidence()

                page["evidence"] = evidence

                if depth < max_depth:
                    for link in evidence["links"]:
                        if (
                            same_origin(
                                link,
                                root_origin,
                            )
                            and link not in queued
                            and likely_html_url(link)
                        ):
                            queued.add(link)

                            heapq.heappush(
                                queue,
                                (
                                    discovery_priority(
                                        link,
                                        depth + 1,
                                    ),
                                    depth + 1,
                                    link,
                                    "page_link",
                                ),
                            )

            except Exception as exc:
                page["parse_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )

        pages.append(page)

    page_type_distribution = {}

    for page in pages:
        evidence = page.get("evidence") or {}
        page_type = evidence.get("page_type")

        if page_type:
            page_type_distribution[page_type] = (
                page_type_distribution.get(
                    page_type,
                    0,
                )
                + 1
            )

    return {
        "schema_version": "site-evidence/v0.2",
        "collector": {
            "name": "site-intelligence",
            "version": "0.2",
        },
        "site": {
            "input_url": start_url,
            "origin": (
                f"{root_origin[0]}://{root_origin[1]}"
            ),
        },
        "crawl": {
            "started_at_unix": time.time(),
            "duration_ms": round(
                (time.monotonic() - started) * 1000
            ),
            "max_pages": max_pages,
            "max_depth": max_depth,
            "max_bytes_per_response": max_bytes,
            "max_seconds": max_seconds,
            "pages_crawled": len(pages),
            "page_type_distribution": page_type_distribution,
        },
        "robots": robots,
        "sitemap": {
            "candidates": normalized_sitemaps,
            "urls_discovered": sitemap_found,
        },
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect bounded website evidence."
    )

    parser.add_argument("url")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
    )
    parser.add_argument(
        "--max-seconds",
        type=int,
        default=DEFAULT_MAX_SECONDS,
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
    )

    args = parser.parse_args()

    if min(
        args.max_pages,
        args.max_depth,
        args.max_bytes,
        args.max_seconds,
        args.timeout,
    ) <= 0:
        parser.error(
            "All numeric limits must be positive."
        )

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
        print(
            json.dumps(
                {"error": str(exc)}
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            bundle,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())