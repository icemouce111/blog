"""Portable source adapters and normalized evidence model for AI Daily."""

from __future__ import annotations

import html
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup


class SourceStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    SKIPPED = "skipped"
    FAILED = "failed"


class SourceTier(str, Enum):
    OFFICIAL = "official"
    COMMUNITY = "community"
    AGGREGATOR = "aggregator"


@dataclass(frozen=True)
class SourceContext:
    target_date: date
    limit: int = 12
    env: Mapping[str, str] = field(default_factory=lambda: os.environ)


@dataclass
class SourceItem:
    source: str
    title: str
    url: str
    summary: str = ""
    published_at: str | None = None
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    author: str | None = None
    engagement: dict[str, int | float | None] = field(default_factory=dict)
    source_tier: SourceTier = SourceTier.AGGREGATOR
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceResult:
    source: str
    status: SourceStatus
    items: list[SourceItem] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def from_dicts(
        cls,
        source: str,
        tier: SourceTier,
        items: Iterable[Mapping[str, Any]],
        *,
        status: SourceStatus = SourceStatus.ACTIVE,
        metadata: Mapping[str, Any] | None = None,
    ) -> "SourceResult":
        normalized = []
        for raw in items:
            title = str(
                raw.get("title")
                or raw.get("name")
                or raw.get("text")
                or ""
            ).strip()
            url = str(raw.get("url") or raw.get("link") or "").strip()
            if not title or not _valid_http_url(url):
                continue
            item_metadata = dict(raw.get("metadata") or {})
            if metadata:
                item_metadata.update(metadata)
            normalized.append(
                SourceItem(
                    source=source,
                    title=title,
                    url=url,
                    summary=str(
                        raw.get("summary")
                        or raw.get("description")
                        or raw.get("desc")
                        or raw.get("selftext")
                        or ""
                    ).strip(),
                    published_at=_normalize_date(
                        raw.get("published_at")
                        or raw.get("date")
                        or raw.get("pubDate")
                    ),
                    author=(
                        str(raw.get("author")).strip()
                        if raw.get("author") is not None
                        else None
                    ),
                    engagement=dict(raw.get("engagement") or {}),
                    source_tier=tier,
                    metadata=item_metadata,
                )
            )
        resolved_status = status if normalized else SourceStatus.SKIPPED
        return cls(source, resolved_status, normalized)


class SourceAdapter(Protocol):
    name: str

    def fetch(self, context: SourceContext) -> SourceResult: ...


class HttpTransport(Protocol):
    def get_text(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: int = 20,
    ) -> str: ...

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: int = 20,
    ) -> Any: ...

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
        timeout: int = 20,
    ) -> Any: ...


class RequestsTransport:
    def get_text(self, url, *, headers=None, timeout=20):
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text

    def get_json(self, url, *, headers=None, timeout=20):
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def post_json(self, url, payload, *, headers=None, timeout=20):
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()


class CallableSource:
    """Wrap an existing fetch function in the normalized source contract."""

    def __init__(
        self,
        name: str,
        tier: SourceTier,
        fetcher: Callable[[], list[Mapping[str, Any]]],
    ):
        self.name = name
        self.tier = tier
        self.fetcher = fetcher

    def fetch(self, context: SourceContext) -> SourceResult:
        try:
            return SourceResult.from_dicts(
                self.name,
                self.tier,
                self.fetcher()[: context.limit],
            )
        except Exception as error:
            return SourceResult(
                self.name,
                SourceStatus.FAILED,
                error=f"{type(error).__name__}: {error}",
            )


class OpenAINewsSource:
    name = "OpenAI"
    url = "https://openai.com/news/rss.xml"

    def __init__(self, transport: HttpTransport | None = None):
        self.transport = transport or RequestsTransport()

    def fetch(self, context: SourceContext) -> SourceResult:
        try:
            items = _parse_rss(self.transport.get_text(self.url))[: context.limit]
            return SourceResult.from_dicts(self.name, SourceTier.OFFICIAL, items)
        except Exception as error:
            return _failed(self.name, error)


class AnthropicNewsSource:
    name = "Anthropic"
    sitemap_url = "https://www.anthropic.com/sitemap.xml"
    newsroom_url = "https://www.anthropic.com/news"

    def __init__(self, transport: HttpTransport | None = None):
        self.transport = transport or RequestsTransport()

    def fetch(self, context: SourceContext) -> SourceResult:
        try:
            sitemap = self.transport.get_text(self.sitemap_url)
            dates = _parse_sitemap_dates(sitemap)
            soup = BeautifulSoup(
                self.transport.get_text(self.newsroom_url),
                "html.parser",
            )
            items = []
            seen = set()
            for anchor in soup.find_all("a", href=True):
                url = urljoin(self.newsroom_url, anchor["href"])
                if "/news/" not in url or url in seen:
                    continue
                title = " ".join(anchor.get_text(" ", strip=True).split())
                if not title:
                    continue
                seen.add(url)
                items.append({
                    "title": title,
                    "url": url,
                    "published_at": dates.get(url),
                })
            return SourceResult.from_dicts(
                self.name,
                SourceTier.OFFICIAL,
                items[: context.limit],
            )
        except Exception as error:
            return _failed(self.name, error)


class LinuxDoSource:
    name = "Linux.do"
    url = "https://linux.do/latest.rss"

    def __init__(
        self,
        transport: HttpTransport | None = None,
        fallback: Callable[[], list[Mapping[str, Any]]] | None = None,
    ):
        self.transport = transport or RequestsTransport()
        self.fallback = fallback

    def fetch(self, context: SourceContext) -> SourceResult:
        try:
            items = _parse_rss(self.transport.get_text(self.url))[: context.limit]
            result = SourceResult.from_dicts(
                self.name,
                SourceTier.COMMUNITY,
                items,
            )
            if result.items:
                return result
        except Exception as error:
            primary_error = error
        else:
            primary_error = RuntimeError("RSS returned no usable topics")
        return _run_fallback(
            self.name,
            SourceTier.COMMUNITY,
            self.fallback,
            primary_error,
            context.limit,
        )


class RedditSource:
    name = "Reddit"

    def __init__(
        self,
        transport: HttpTransport | None = None,
        *,
        subreddits: tuple[str, ...] = (
            "MachineLearning",
            "LocalLLaMA",
            "ClaudeCode",
            "OpenAI",
            "ArtificialIntelligence",
        ),
        fallback: Callable[[], list[Mapping[str, Any]]] | None = None,
    ):
        self.transport = transport or RequestsTransport()
        self.subreddits = subreddits
        self.fallback = fallback

    def fetch(self, context: SourceContext) -> SourceResult:
        items = []
        errors = []
        per_subreddit = max(5, min(context.limit, 25))
        headers = {"User-Agent": "ai-daily/1.0"}
        for subreddit in self.subreddits:
            url = (
                f"https://www.reddit.com/r/{subreddit}/hot.json"
                f"?limit={per_subreddit}"
            )
            try:
                payload = self.transport.get_json(url, headers=headers)
                for child in payload.get("data", {}).get("children", []):
                    post = child.get("data") or {}
                    permalink = post.get("permalink") or ""
                    items.append({
                        "title": post.get("title"),
                        "url": urljoin("https://www.reddit.com", permalink),
                        "summary": post.get("selftext") or "",
                        "published_at": _epoch_date(post.get("created_utc")),
                        "author": post.get("author"),
                        "engagement": {
                            "score": post.get("score", 0),
                            "comments": post.get("num_comments", 0),
                        },
                    })
            except Exception as error:
                errors.append(f"{subreddit}: {error}")
        result = SourceResult.from_dicts(
            self.name,
            SourceTier.COMMUNITY,
            items[: context.limit],
        )
        if result.items:
            if errors:
                result.status = SourceStatus.DEGRADED
                result.error = "; ".join(errors)
            return result
        return _run_fallback(
            self.name,
            SourceTier.COMMUNITY,
            self.fallback,
            RuntimeError("; ".join(errors) or "public Reddit returned no items"),
            context.limit,
        )


class XSource:
    name = "X/Twitter"
    endpoint = "https://api.x.com/2/tweets/search/recent"

    def __init__(
        self,
        transport: HttpTransport | None = None,
        *,
        query: str = "AI OR LLM",
        fallback: Callable[[], list[Mapping[str, Any]]] | None = None,
    ):
        self.transport = transport or RequestsTransport()
        self.query = query
        self.fallback = fallback

    @classmethod
    def recent_search_url(cls, query: str, limit: int) -> str:
        params = {
            "query": f"({query}) -is:retweet",
            "max_results": max(10, min(100, limit)),
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username",
        }
        return f"{cls.endpoint}?{urlencode(params)}"

    def fetch(self, context: SourceContext) -> SourceResult:
        token = context.env.get("X_BEARER_TOKEN")
        if token:
            try:
                payload = self.transport.get_json(
                    self.recent_search_url(self.query, context.limit),
                    headers={"Authorization": f"Bearer {token}"},
                )
                users = {
                    user["id"]: user
                    for user in payload.get("includes", {}).get("users", [])
                }
                items = []
                for post in payload.get("data", []):
                    username = users.get(post.get("author_id"), {}).get(
                        "username",
                        "",
                    )
                    post_id = post.get("id")
                    if not username or not post_id:
                        continue
                    metrics = post.get("public_metrics") or {}
                    items.append({
                        "title": post.get("text"),
                        "summary": post.get("text"),
                        "url": f"https://x.com/{username}/status/{post_id}",
                        "author": username,
                        "published_at": post.get("created_at"),
                        "engagement": {
                            "likes": metrics.get("like_count", 0),
                            "reposts": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "quotes": metrics.get("quote_count", 0),
                        },
                    })
                result = SourceResult.from_dicts(
                    self.name,
                    SourceTier.COMMUNITY,
                    items,
                    metadata={"retrieval": "official-api"},
                )
                if result.items:
                    return result
                primary_error = RuntimeError("official X API returned no items")
            except Exception as error:
                primary_error = error
        else:
            primary_error = RuntimeError("X_BEARER_TOKEN is not configured")
        return _run_fallback(
            self.name,
            SourceTier.COMMUNITY,
            self.fallback,
            primary_error,
            context.limit,
        )


class XiaohongshuSource:
    name = "Xiaohongshu"

    def __init__(
        self,
        transport: HttpTransport | None = None,
        *,
        query: str = "AI 人工智能",
        fallback: Callable[[], list[Mapping[str, Any]]] | None = None,
    ):
        self.transport = transport or RequestsTransport()
        self.query = query
        self.fallback = fallback

    def fetch(self, context: SourceContext) -> SourceResult:
        base = (context.env.get("XIAOHONGSHU_API_BASE") or "").rstrip("/")
        if base:
            try:
                login = self.transport.get_json(
                    f"{base}/api/v1/login/status",
                    timeout=8,
                )
                if not login.get("data", {}).get("is_logged_in"):
                    raise RuntimeError("Xiaohongshu MCP is not logged in")
                payload = {
                    "keyword": self.query,
                    "filters": {
                        "sort_by": "综合",
                        "note_type": "不限",
                        "publish_time": "一周内",
                        "search_scope": "不限",
                        "location": "不限",
                    },
                }
                response = self.transport.post_json(
                    f"{base}/api/v1/feeds/search",
                    payload,
                )
                items = []
                for feed in response.get("data", {}).get("feeds", []):
                    note = feed.get("noteCard") or {}
                    feed_id = feed.get("id") or note.get("noteId")
                    if not feed_id:
                        continue
                    token = feed.get("xsecToken") or note.get("xsecToken") or ""
                    url = f"https://www.xiaohongshu.com/explore/{feed_id}"
                    if token:
                        url += f"?xsec_token={token}"
                    interactions = note.get("interactInfo") or {}
                    user = note.get("user") or {}
                    items.append({
                        "title": note.get("displayTitle") or note.get("title"),
                        "summary": note.get("desc") or "",
                        "url": url,
                        "author": user.get("nickname"),
                        "published_at": _milliseconds_date(note.get("time")),
                        "engagement": {
                            "likes": _chinese_count(
                                interactions.get("likedCount")
                            ),
                            "comments": _chinese_count(
                                interactions.get("commentCount")
                            ),
                            "favorites": _chinese_count(
                                interactions.get("collectedCount")
                            ),
                        },
                    })
                result = SourceResult.from_dicts(
                    self.name,
                    SourceTier.COMMUNITY,
                    items[: context.limit],
                    metadata={"retrieval": "xiaohongshu-mcp"},
                )
                if result.items:
                    return result
                primary_error = RuntimeError(
                    "Xiaohongshu MCP returned no usable notes"
                )
            except Exception as error:
                primary_error = error
        else:
            primary_error = RuntimeError(
                "XIAOHONGSHU_API_BASE is not configured"
            )
        return _run_fallback(
            self.name,
            SourceTier.COMMUNITY,
            self.fallback,
            primary_error,
            context.limit,
        )


class SourceRegistry:
    def __init__(self, adapters: Iterable[SourceAdapter]):
        self.adapters = list(adapters)

    def fetch_all(self, context: SourceContext) -> dict[str, SourceResult]:
        fetched: dict[str, SourceResult] = {}
        with ThreadPoolExecutor(
            max_workers=max(1, min(8, len(self.adapters)))
        ) as executor:
            futures = {
                executor.submit(adapter.fetch, context): adapter
                for adapter in self.adapters
            }
            for future in as_completed(futures):
                adapter = futures[future]
                try:
                    fetched[adapter.name] = future.result()
                except Exception as error:
                    fetched[adapter.name] = _failed(adapter.name, error)

        seen_urls = set()
        ordered = {}
        for adapter in self.adapters:
            result = fetched[adapter.name]
            deduplicated = []
            for item in result.items:
                key = _canonical_url(item.url)
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                deduplicated.append(item)
            result.items = deduplicated
            ordered[adapter.name] = result
        return ordered


def _failed(source: str, error: Exception) -> SourceResult:
    return SourceResult(
        source,
        SourceStatus.FAILED,
        error=f"{type(error).__name__}: {error}",
    )


def _run_fallback(
    source: str,
    tier: SourceTier,
    fallback: Callable[[], list[Mapping[str, Any]]] | None,
    primary_error: Exception,
    limit: int,
) -> SourceResult:
    if fallback is None:
        return SourceResult(
            source,
            SourceStatus.SKIPPED,
            error=str(primary_error),
        )
    try:
        result = SourceResult.from_dicts(
            source,
            tier,
            fallback()[:limit],
            status=SourceStatus.DEGRADED,
            metadata={"retrieval": "browser-fallback"},
        )
        result.error = str(primary_error)
        return result
    except Exception as error:
        return SourceResult(
            source,
            SourceStatus.FAILED,
            error=f"{primary_error}; fallback failed: {error}",
        )


def _parse_rss(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    items = []
    for node in root.findall(".//item"):
        items.append({
            "title": _node_text(node, "title"),
            "url": _node_text(node, "link"),
            "summary": _strip_html(
                _node_text(node, "description")
                or _node_text(node, "content")
            ),
            "published_at": _node_text(node, "pubDate"),
            "author": _node_text(node, "author") or None,
        })
    return items


def _parse_sitemap_dates(xml_text: str) -> dict[str, str]:
    root = ET.fromstring(xml_text)
    dates = {}
    for node in root.findall(".//{*}url"):
        location = node.findtext("{*}loc")
        modified = node.findtext("{*}lastmod")
        if location and "/news/" in location:
            dates[location.strip()] = (modified or "").strip()
    return dates


def _node_text(node: ET.Element, name: str) -> str:
    child = node.find(name)
    if child is None:
        child = node.find(f"{{*}}{name}")
    return (child.text or "").strip() if child is not None else ""


def _strip_html(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(html.unescape(value), "html.parser").get_text(" ")
    return " ".join(text.split())


def _normalize_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return text
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _epoch_date(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _milliseconds_date(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(
            float(value) / 1000,
            timezone.utc,
        ).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _chinese_count(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().replace(",", "")
    try:
        if text.endswith("万"):
            return int(float(text[:-1]) * 10_000)
        if text.endswith("亿"):
            return int(float(text[:-1]) * 100_000_000)
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def _valid_http_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower().removeprefix("www."),
        parsed.path.rstrip("/"),
        urlencode(params),
        "",
    ))
