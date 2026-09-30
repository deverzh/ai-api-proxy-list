"""
Discover API-related metadata from provider official websites.

This script parses providers from README.md, fetches each homepage plus a
small set of likely documentation pages, extracts possible API base URLs, and
writes an auditable JSON report. It intentionally does not edit README.md:
review the generated data before promoting fields into the public table.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import html
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
README_PATH = ROOT / "README.md"
DEFAULT_OUTPUT = ROOT / "provider_api_info.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

LIKELY_DOC_PATHS = (
    "/docs",
    "/doc",
    "/api",
    "/api-docs",
    "/docs/api",
    "/developer",
    "/developers",
    "/platform",
    "/pricing",
)

LINK_HINTS = (
    "api",
    "doc",
    "docs",
    "developer",
    "openai",
    "model",
    "pricing",
    "接入",
    "文档",
    "接口",
    "模型",
)

TEXT_HINT_RE = re.compile(
    r"(base\s*url|baseurl|api[_\-\s]*base|endpoint|openai|"
    r"api\s*url|接口地址|请求地址|基础地址|中转地址|代理地址|兼容地址|模型列表)",
    re.IGNORECASE,
)

URL_RE = re.compile(
    r"https?://[a-zA-Z0-9][a-zA-Z0-9.-]*(?::\d+)?"
    r"(?:/[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?"
)

BASE_URL_RE = re.compile(
    r"https?://[a-zA-Z0-9][a-zA-Z0-9.-]*(?::\d+)?"
    r"(?:/(?:v\d+|api(?:/v\d+)?|openai(?:/v\d+)?|api/openai(?:/v\d+)?|oneapi(?:/v\d+)?))/?",
    re.IGNORECASE,
)

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
LINK_RE = re.compile(
    r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class Provider:
    index: int
    name: str
    homepage: str
    models: str
    latency: str


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None = None
    elapsed_ms: int | None = None
    final_url: str | None = None
    title: str | None = None
    content_type: str | None = None
    error: str | None = None
    text: str = ""


@dataclass
class Candidate:
    url: str
    source_url: str
    confidence: str
    reason: str
    evidence: str = ""
    status: int | None = None
    elapsed_ms: int | None = None


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def strip_tags(markup: str) -> str:
    markup = SCRIPT_STYLE_RE.sub(" ", markup)
    markup = re.sub(r"<br\s*/?>", "\n", markup, flags=re.IGNORECASE)
    markup = re.sub(r"</p\s*>|</div\s*>|</li\s*>|</tr\s*>", "\n", markup, flags=re.IGNORECASE)
    return normalize_ws(TAG_RE.sub(" ", markup))


def parse_readme(path: Path) -> list[Provider]:
    content = path.read_text(encoding="utf-8")
    row_re = re.compile(
        r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*"
        r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|$",
        re.MULTILINE,
    )
    providers: list[Provider] = []
    for match in row_re.finditer(content):
        providers.append(
            Provider(
                index=int(match.group(1)),
                name=normalize_ws(match.group(2)),
                homepage=match.group(4).strip(),
                models=normalize_ws(match.group(5)),
                latency=normalize_ws(match.group(6)),
            )
        )
    return providers


def request_url(url: str, timeout: float, max_bytes: int = 600_000) -> FetchResult:
    started = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(max_bytes)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            title_match = TITLE_RE.search(text)
            title = normalize_ws(title_match.group(1)) if title_match else None
            return FetchResult(
                url=url,
                ok=True,
                status=response.status,
                elapsed_ms=elapsed_ms,
                final_url=response.geturl(),
                title=title,
                content_type=content_type,
                text=text,
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read(max_bytes)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        charset = exc.headers.get_content_charset() if exc.headers else None
        text = raw.decode(charset or "utf-8", errors="replace")
        title_match = TITLE_RE.search(text)
        title = normalize_ws(title_match.group(1)) if title_match else None
        return FetchResult(
            url=url,
            ok=True,
            status=exc.code,
            elapsed_ms=elapsed_ms,
            final_url=exc.geturl(),
            title=title,
            content_type=exc.headers.get("Content-Type", "") if exc.headers else None,
            text=text,
        )
    except Exception as exc:
        return FetchResult(
            url=url,
            ok=False,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


def hostname(url: str) -> str:
    return urllib.parse.urlparse(url).hostname or ""


def same_site_or_api_subdomain(base_url: str, target_url: str) -> bool:
    base_host = hostname(base_url).removeprefix("www.")
    target_host = hostname(target_url).removeprefix("www.")
    if not base_host or not target_host:
        return False
    return target_host == base_host or target_host.endswith("." + base_host)


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+$", "", parsed.path or "")
    return urllib.parse.urlunparse((scheme, netloc, path, "", "", ""))


def discover_links(homepage: str, text: str, max_links: int) -> list[str]:
    links: list[str] = []
    seen = set()
    for raw_href, label_html in LINK_RE.findall(text):
        label = strip_tags(label_html).lower()
        href = html.unescape(raw_href).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urllib.parse.urljoin(homepage, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        haystack = f"{parsed.path} {parsed.query} {label}".lower()
        if not any(hint.lower() in haystack for hint in LINK_HINTS):
            continue
        if not same_site_or_api_subdomain(homepage, absolute):
            continue
        normalized = normalize_url(absolute)
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
        if len(links) >= max_links:
            break
    return links


def likely_doc_urls(homepage: str, max_links: int) -> list[str]:
    parsed = urllib.parse.urlparse(homepage)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    urls = [normalize_url(urllib.parse.urljoin(origin, path)) for path in LIKELY_DOC_PATHS]
    return urls[:max_links]


def evidence_around(text: str, needle: str, radius: int = 100) -> str:
    idx = text.lower().find(needle.lower())
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return normalize_ws(text[start:end])


def looks_like_api_base(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.lower().rstrip("/")
    return (
        host.startswith("api.")
        or "/v1" in path
        or path.endswith("/api")
        or "/openai" in path
        or "/oneapi" in path
    )


def extract_candidates(page: FetchResult, homepage: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    if not page.text:
        return candidates

    plain = strip_tags(page.text)
    for match in BASE_URL_RE.finditer(page.text):
        url = normalize_url(html.unescape(match.group(0)).strip("`'\".,;，。"))
        evidence = evidence_around(plain, urllib.parse.urlparse(url).netloc)
        candidates.append(
            Candidate(
                url=url,
                source_url=page.final_url or page.url,
                confidence="high" if TEXT_HINT_RE.search(evidence) else "medium",
                reason="explicit API-like URL found in page",
                evidence=evidence[:260],
            )
        )

    for match in URL_RE.finditer(page.text):
        url = normalize_url(html.unescape(match.group(0)).strip("`'\".,;，。"))
        if not looks_like_api_base(url):
            continue
        if not same_site_or_api_subdomain(homepage, url):
            continue
        evidence = evidence_around(plain, urllib.parse.urlparse(url).netloc)
        candidates.append(
            Candidate(
                url=url,
                source_url=page.final_url or page.url,
                confidence="medium",
                reason="same-site URL looks like an API endpoint",
                evidence=evidence[:260],
            )
        )

    return dedupe_candidates(candidates)


def dedupe_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    rank = {"high": 3, "medium": 2, "low": 1}
    by_url: dict[str, Candidate] = {}
    for candidate in candidates:
        key = normalize_url(candidate.url)
        existing = by_url.get(key)
        if existing is None or rank[candidate.confidence] > rank[existing.confidence]:
            candidate.url = key
            by_url[key] = candidate
    return sorted(by_url.values(), key=lambda c: (-rank[c.confidence], c.url))


def check_tcp(host: str, port: int = 443, timeout: float = 3.0) -> int | None:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return int((time.perf_counter() - started) * 1000)
    except Exception:
        return None


def add_inferred_candidates(provider: Provider, timeout: float) -> list[Candidate]:
    parsed = urllib.parse.urlparse(provider.homepage)
    base_host = (parsed.hostname or "").removeprefix("www.")
    if not base_host:
        return []

    inferred: list[Candidate] = []
    for host in (f"api.{base_host}", base_host):
        tcp_ms = check_tcp(host, 443, timeout=min(timeout, 3.0))
        if tcp_ms is None:
            continue
        url = f"https://{host}/v1"
        inferred.append(
            Candidate(
                url=url,
                source_url=provider.homepage,
                confidence="low",
                reason="inferred from reachable host; not confirmed by page text",
                elapsed_ms=tcp_ms,
            )
        )
    return dedupe_candidates(inferred)


def validate_candidates(candidates: list[Candidate], timeout: float, max_candidates: int) -> list[Candidate]:
    for candidate in candidates[:max_candidates]:
        parsed = urllib.parse.urlparse(candidate.url)
        if candidate.status is not None or not parsed.hostname:
            continue
        probe_url = candidate.url.rstrip("/") + "/models"
        result = request_url(probe_url, timeout=timeout, max_bytes=80_000)
        candidate.status = result.status
        candidate.elapsed_ms = result.elapsed_ms
    return candidates


def scan_provider(
    provider: Provider,
    timeout: float,
    max_pages: int,
    max_links: int,
    max_candidates: int,
    validate: bool,
    infer: bool,
) -> dict:
    homepage = request_url(provider.homepage, timeout=timeout)
    pages = [homepage]

    urls_to_fetch: list[str] = []
    seen_urls = {normalize_url(provider.homepage)}
    if homepage.text:
        urls_to_fetch.extend(discover_links(provider.homepage, homepage.text, max_links=max_links))
    urls_to_fetch.extend(likely_doc_urls(provider.homepage, max_links=max_links))

    for url in urls_to_fetch:
        normalized = normalize_url(url)
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)
        if len(pages) >= max_pages:
            break
        pages.append(request_url(normalized, timeout=timeout))

    candidates: list[Candidate] = []
    for page in pages:
        if page.ok:
            candidates.extend(extract_candidates(page, provider.homepage))
    if infer:
        candidates.extend(add_inferred_candidates(provider, timeout=timeout))
    candidates = dedupe_candidates(candidates)
    if validate:
        candidates = validate_candidates(candidates, timeout=timeout, max_candidates=max_candidates)

    return {
        "index": provider.index,
        "name": provider.name,
        "homepage": provider.homepage,
        "models_from_readme": provider.models,
        "latency_from_readme": provider.latency,
        "checked_at": now_iso(),
        "homepage_status": homepage.status,
        "homepage_ms": homepage.elapsed_ms,
        "homepage_title": homepage.title,
        "pages_checked": [
            {
                "url": page.url,
                "ok": page.ok,
                "status": page.status,
                "elapsed_ms": page.elapsed_ms,
                "final_url": page.final_url,
                "title": page.title,
                "content_type": page.content_type,
                "error": page.error,
            }
            for page in pages
        ],
        "api_base_url_candidates": [asdict(candidate) for candidate in candidates],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=README_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None, help="Scan only the first N providers.")
    parser.add_argument("--start", type=int, default=1, help="Start from README provider index.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--max-links", type=int, default=8)
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--no-validate", action="store_true", help="Skip /models probes for candidates.")
    parser.add_argument("--no-infer", action="store_true", help="Do not infer api.<domain>/v1 candidates.")
    args = parser.parse_args()
    socket.setdefaulttimeout(args.timeout)

    providers = [p for p in parse_readme(args.readme) if p.index >= args.start]
    if args.limit is not None:
        providers = providers[: args.limit]

    print(f"Scanning {len(providers)} providers from {args.readme}")
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(
                scan_provider,
                provider,
                args.timeout,
                args.max_pages,
                args.max_links,
                args.max_candidates,
                not args.no_validate,
                not args.no_infer,
            ): provider
            for provider in providers
        }
        for future in concurrent.futures.as_completed(future_map):
            provider = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "index": provider.index,
                    "name": provider.name,
                    "homepage": provider.homepage,
                    "checked_at": now_iso(),
                    "error": f"{type(exc).__name__}: {exc}",
                    "api_base_url_candidates": [],
                }
            results.append(result)
            candidates = result.get("api_base_url_candidates", [])
            best = candidates[0]["url"] if candidates else "-"
            print(
                f"{provider.index:3d}. {provider.name[:28]:28s} "
                f"candidates={len(candidates):2d} best={best}",
                flush=True,
            )

    results.sort(key=lambda item: item.get("index", 999999))
    output = {
        "generated_at": now_iso(),
        "source_readme": str(args.readme),
        "provider_count": len(results),
        "notes": [
            "high/medium candidates were found in fetched page text or links.",
            "low candidates are inferred from reachable api.<domain>/v1 or <domain>/v1 and need manual review.",
            "status/elapsed_ms on a candidate comes from probing <candidate>/models; 401/403 may still mean the base URL exists.",
        ],
        "providers": results,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
