"""
Discover API Base URL from provider websites, test its latency,
and update README.md with new columns: Base URL, API latency.
Sorting: first by API Base URL latency, then by homepage latency.

Improvements:
1. Better API discovery: look for api.xxx subdomains
2. Handle latency consistency when Base URL == homepage
3. Re-test both homepage and API latency on each run
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
README_PATH = ROOT / "README.md"
CACHE_PATH = ROOT / "api_base_url_cache.json"

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
)

LINK_HINTS = (
    "api",
    "doc",
    "docs",
    "developer",
    "openai",
    "model",
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
    latency: str = ""
    api_base_url: str = ""
    api_latency: str = ""


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


def parse_readme(path: Path) -> tuple[list[Provider], str]:
    content = path.read_text(encoding="utf-8")

    table_start = content.find("| # | 名称 | 官网 |")
    table_end = content.find("\n\n---\n\n## 📚", table_start)
    if table_end == -1:
        table_end = content.find("\n\n## 📚", table_start)

    if table_start == -1 or table_end == -1:
        return [], content

    table_text = content[table_start:table_end]

    providers: list[Provider] = []
    row_re_old = re.compile(
        r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*"
        r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|$",
        re.MULTILINE,
    )
    row_re_new = re.compile(
        r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*"
        r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$",
        re.MULTILINE,
    )

    for match in row_re_new.finditer(table_text):
        providers.append(
            Provider(
                index=int(match.group(1)),
                name=normalize_ws(match.group(2)),
                homepage=match.group(4).strip(),
                models=normalize_ws(match.group(5)),
                api_base_url=normalize_ws(match.group(6)),
                api_latency=normalize_ws(match.group(7)),
                latency=normalize_ws(match.group(8)),
            )
        )

    if not providers:
        for match in row_re_old.finditer(table_text):
            providers.append(
                Provider(
                    index=int(match.group(1)),
                    name=normalize_ws(match.group(2)),
                    homepage=match.group(4).strip(),
                    models=normalize_ws(match.group(5)),
                    latency=normalize_ws(match.group(6)),
                )
            )

    return providers, content


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


def base_url_without_path(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


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
    rank = {"high": 4, "medium": 3, "inferred": 2, "fallback": 1, "homepage": 0}
    by_url: dict[str, Candidate] = {}
    for candidate in candidates:
        key = normalize_url(candidate.url)
        existing = by_url.get(key)
        if existing is None or rank[candidate.confidence] > rank[existing.confidence]:
            candidate.url = key
            by_url[key] = candidate
    return sorted(by_url.values(), key=lambda c: (-rank[c.confidence], c.url))


def test_api_base_url(base_url: str, timeout: float = 10.0) -> tuple[int | None, str | None]:
    """
    Test if a URL is a valid API Base URL by checking common OpenAI-compatible endpoints.
    Returns (latency_ms, error_message). latency_ms is None if not valid.
    """
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or ""
    if not host:
        return None, "Invalid URL"
    
    test_paths = [
        "/v1/models",
        "/v1/models/",
        "/v1",
        "/api/v1/models",
        "/openai/v1/models",
        "/",
    ]
    
    for test_path in test_paths:
        full_url = base_url.rstrip("/") + test_path
        started = time.perf_counter()
        
        try:
            req = urllib.request.Request(full_url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }, method="GET")
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                
                if 200 <= status < 400:
                    if "json" in content_type.lower():
                        return elapsed_ms, None
                    else:
                        try:
                            data = response.read(2000).decode("utf-8", errors="ignore")
                            if '"model' in data.lower() or '"data"' in data.lower():
                                return elapsed_ms, None
                        except:
                            pass
                
                if status == 401 or status == 403:
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    return elapsed_ms, None
                    
        except urllib.error.HTTPError as e:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if e.code == 401 or e.code == 403:
                return elapsed_ms, None
            elif e.code == 404:
                continue
            elif 400 <= e.code < 500:
                return elapsed_ms, None
        except Exception:
            continue
    
    return None, "No valid API endpoint found"


def test_homepage_latency(homepage: str, timeout: float = 10.0) -> int | None:
    """
    Test homepage latency using actual HTTP request.
    """
    try:
        started = time.perf_counter()
        req = urllib.request.Request(homepage, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read(2048)
            return int((time.perf_counter() - started) * 1000)
    except Exception:
        return None


def add_inferred_candidates(homepage: str) -> list[Candidate]:
    """
    Add inferred API candidates (api.xxx.com) for testing.
    """
    parsed = urllib.parse.urlparse(homepage)
    base_host = (parsed.hostname or "").removeprefix("www.")
    if not base_host:
        return []

    inferred: list[Candidate] = []
    
    if not base_host.startswith("api."):
        api_host = f"api.{base_host}"
        api_base_url = f"https://{api_host}"
        inferred.append(
            Candidate(
                url=api_base_url,
                source_url=homepage,
                confidence="inferred",
                reason="inferred: api subdomain",
            )
        )
    
    return inferred


def validate_candidates(candidates: list[Candidate], timeout: float, max_candidates: int) -> list[Candidate]:
    """
    Validate candidates using actual API endpoint tests.
    """
    validated = []
    for candidate in candidates[:max_candidates]:
        parsed = urllib.parse.urlparse(candidate.url)
        if not parsed.hostname:
            continue
        
        base_url = base_url_without_path(candidate.url)
        latency, error = test_api_base_url(base_url, timeout=timeout)
        
        if latency is not None:
            candidate.elapsed_ms = latency
            candidate.status = 200
            validated.append(candidate)
    
    return validated


def select_best_candidate(candidates: list[Candidate], homepage: str) -> tuple[str, int | None]:
    if not candidates:
        return "", None

    rank = {"high": 5, "medium": 4, "inferred": 3, "fallback": 2, "homepage": 1}
    
    validated = [c for c in candidates if c.elapsed_ms is not None]
    
    if validated:
        validated.sort(key=lambda c: (-rank.get(c.confidence, 0), c.elapsed_ms or 999999))
        best = validated[0]
        base_url = base_url_without_path(best.url)
        return base_url, best.elapsed_ms
    
    return "", None


def scan_provider(
    provider: Provider,
    timeout: float,
    max_pages: int,
    max_links: int,
    max_candidates: int,
    validate: bool,
) -> Provider:
    try:
        homepage_result = request_url(provider.homepage, timeout=timeout)
        pages = [homepage_result]

        urls_to_fetch: list[str] = []
        seen_urls = {normalize_url(provider.homepage)}
        if homepage_result.text:
            urls_to_fetch.extend(discover_links(provider.homepage, homepage_result.text, max_links=max_links))
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
        
        inferred = add_inferred_candidates(provider.homepage)
        candidates.extend(inferred)
        
        candidates = dedupe_candidates(candidates)
        
        if validate and candidates:
            candidates = validate_candidates(candidates, timeout=timeout, max_candidates=max_candidates)
        
        api_base_url, api_latency_ms = select_best_candidate(candidates, provider.homepage)
        
        homepage_latency_ms = test_homepage_latency(provider.homepage, timeout=timeout)
        if homepage_latency_ms is not None:
            provider.latency = f"{homepage_latency_ms}ms"
        else:
            provider.latency = "超时"
        
        if api_base_url:
            if api_latency_ms is not None:
                provider.api_base_url = api_base_url
                provider.api_latency = f"{api_latency_ms}ms"
            else:
                provider.api_base_url = api_base_url
                provider.api_latency = "未知"
            
            if base_url_without_path(api_base_url) == base_url_without_path(provider.homepage):
                provider.api_latency = provider.latency
        else:
            provider.api_base_url = "待确认"
            provider.api_latency = "-"

    except Exception as exc:
        print(f"  Error scanning {provider.name}: {exc}")
        provider.api_base_url = "待确认"
        provider.api_latency = "-"
        if not provider.latency:
            provider.latency = "超时"

    return provider


def load_cache() -> dict[str, dict]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict[str, dict]):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def sort_key(provider: Provider) -> tuple[int, int, int, int, str]:
    api_latency_val = 999999
    if provider.api_latency and provider.api_latency != "-" and provider.api_latency != "未知":
        try:
            api_latency_val = int(provider.api_latency.replace("ms", ""))
        except ValueError:
            pass

    homepage_latency_val = 999999
    if provider.latency and provider.latency != "超时" and provider.latency != "-":
        try:
            homepage_latency_val = int(provider.latency.replace("ms", ""))
        except ValueError:
            pass

    api_priority = 0 if api_latency_val < 999999 else 1
    homepage_priority = 0 if homepage_latency_val < 999999 else 1

    return (api_priority, api_latency_val, homepage_priority, homepage_latency_val, provider.name.lower())


def build_table(providers: list[Provider]) -> str:
    header = "| # | 名称 | 官网 | 支持模型 | Base URL | API延迟 | 官网延迟 |"
    align = "|:---:|:---|:---|:---|:---|:---:|:---:|"

    lines = [header, align]
    for i, provider in enumerate(providers, 1):
        domain = urllib.parse.urlparse(provider.homepage).netloc
        link_text = domain

        if provider.api_base_url and provider.api_base_url != "待确认" and provider.api_base_url != "-":
            api_url_display = f"[{urllib.parse.urlparse(provider.api_base_url).netloc}]({provider.api_base_url})"
        else:
            api_url_display = provider.api_base_url or "-"

        line = (
            f"| {i} | {provider.name} | [{link_text}]({provider.homepage}) | "
            f"{provider.models} | {api_url_display} | {provider.api_latency or '-'} | {provider.latency or '-'} |"
        )
        lines.append(line)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=README_PATH)
    parser.add_argument("--limit", type=int, default=None, help="Scan only the first N providers.")
    parser.add_argument("--start", type=int, default=1, help="Start from provider index.")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--max-links", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--no-cache", action="store_true", help="Skip using cached results.")
    parser.add_argument("--rescan-failed", action="store_true", help="Rescan entries with '待确认'.")
    args = parser.parse_args()
    socket.setdefaulttimeout(args.timeout)

    providers, content = parse_readme(args.readme)
    if not providers:
        print("No providers found in README.")
        return 1

    original_count = len(providers)
    providers = [p for p in providers if p.index >= args.start]
    if args.limit is not None:
        providers = providers[: args.limit]

    cache = {} if args.no_cache else load_cache()

    print(f"Scanning {len(providers)} providers (total in table: {original_count})")
    print("Features:")
    print("  - Re-testing homepage latency for each provider")
    print("  - Testing API Base URL using actual API endpoints (/v1/models, etc.)")
    print("  - Looking for api.xxx subdomains")
    print("  - Using same latency when Base URL == homepage URL")

    providers_to_scan = []
    cached_results = []

    for provider in providers:
        cache_key = provider.homepage
        if not args.no_cache and cache_key in cache:
            cached = cache[cache_key]
            if not args.rescan_failed or (provider.api_base_url != "待确认" and provider.api_base_url):
                provider.api_base_url = cached.get("api_base_url", provider.api_base_url)
                provider.api_latency = cached.get("api_latency", provider.api_latency)
                provider.latency = cached.get("homepage_latency", provider.latency)
                cached_results.append(provider)
                continue
        providers_to_scan.append(provider)

    print(f"\n  Using cache: {len(cached_results)}, to scan: {len(providers_to_scan)}")

    results: list[Provider] = cached_results[:]
    total_to_scan = len(providers_to_scan)
    completed = 0

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
            ): provider
            for provider in providers_to_scan
        }
        for future in concurrent.futures.as_completed(future_map):
            provider = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"  Error for {provider.name}: {exc}")
                result = provider
                result.api_base_url = "待确认"
                result.api_latency = "-"
                if not result.latency:
                    result.latency = "超时"

            results.append(result)
            cache[provider.homepage] = {
                "api_base_url": result.api_base_url,
                "api_latency": result.api_latency,
                "homepage_latency": result.latency,
                "updated_at": now_iso(),
            }
            completed += 1
            progress = f"[{completed}/{total_to_scan}]"
            print(
                f"{progress} {provider.index:3d}. {provider.name[:25]:25s} "
                f"API URL: {result.api_base_url[:40]:40s} "
                f"API latency: {result.api_latency:10s} "
                f"Homepage latency: {result.latency}",
                flush=True
            )

            if not args.no_cache and completed % 10 == 0:
                save_cache(cache)
                print(f"  (Saved cache after {completed} scans)", flush=True)

    if not args.no_cache:
        save_cache(cache)

    all_providers = {p.homepage: p for p in results}

    full_providers, _ = parse_readme(args.readme)
    for p in full_providers:
        if p.homepage in all_providers:
            cached = all_providers[p.homepage]
            p.api_base_url = cached.api_base_url
            p.api_latency = cached.api_latency
            p.latency = cached.latency
        elif not p.api_base_url:
            p.api_base_url = "待确认"
            p.api_latency = "-"

    full_providers.sort(key=sort_key)

    new_table = build_table(full_providers)

    table_start = content.find("| # | 名称 | 官网 |")
    table_end = content.find("\n\n---\n\n## 📚", table_start)
    if table_end == -1:
        table_end = content.find("\n\n## 📚", table_start)

    if table_start == -1 or table_end == -1:
        print("Could not find table boundaries in README.")
        return 1

    old_table = content[table_start:table_end]
    new_content = content[:table_start] + new_table + content[table_end:]

    args.readme.write_text(new_content, encoding="utf-8")

    confirmed = sum(1 for p in full_providers if p.api_base_url and p.api_base_url != "待确认" and p.api_base_url != "-")
    pending = len(full_providers) - confirmed

    print(f"\nUpdated README with {len(full_providers)} providers.")
    print(f"  Confirmed API Base URL: {confirmed}")
    print(f"  Pending (待确认): {pending}")
    print("Sorting: first by API Base URL latency, then by homepage latency.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
