"""AIHOT selected items, kept as attributed secondary evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlencode, urlsplit

import requests

try:
    from scripts.ai_daily_editorial import prioritize_items
    from scripts.ai_daily_sources import SourceResult, SourceStatus, SourceTier, SignalType
except ModuleNotFoundError:
    from ai_daily_editorial import prioritize_items
    from ai_daily_sources import SourceResult, SourceStatus, SourceTier, SignalType


class AIHOTSource:
    name = "AIHOT"
    supports_historical = False
    signal_type = SignalType.STORY

    def __init__(self, profile, *, request=None, cache_dir=None):
        self.profile = profile
        self.settings = profile["aihot"]
        self.request = request or requests.get
        self.url = "https://aihot.news/api/v1/items?" + urlencode({
            "mode": "selected", "window": "24h", "by": "published",
            "limit": self.settings["fetchLimit"],
        })
        directory = (
            Path(cache_dir) if cache_dir is not None
            else Path(tempfile.gettempdir()) / "ai-daily-aihot"
        )
        self.cache_path = directory / (hashlib.sha256(self.url.encode()).hexdigest() + ".json")

    def _payload(self):
        try:
            cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(cache, dict):
                cache = {}
            cached_payload = cache.get("payload")
            if (
                cache.get("url") != self.url
                or not isinstance(cached_payload, dict)
                or not isinstance(cached_payload.get("items"), list)
                or not isinstance(cache.get("expires_at"), (int, float))
            ):
                cache = {}
        except (OSError, ValueError, AttributeError):
            cache = {}
        now = time.time()
        if cache and now < cache.get("expires_at", 0):
            return cache["payload"]
        headers = {"User-Agent": "aihot-api/2.0.0", "Accept": "application/json", "Accept-Encoding": "gzip"}
        if cache.get("etag"):
            headers["If-None-Match"] = cache["etag"]
        response = self.request(
            self.url, headers=headers,
            timeout=self.settings["timeoutSeconds"], allow_redirects=False,
        )
        if response.status_code == 304:
            if not cache:
                raise ValueError("AIHOT returned 304 without a cached response")
            payload = cache["payload"]
        elif response.status_code == 200:
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                raise ValueError("AIHOT returned an invalid items response")
        else:
            # No retry in this run: never race a provider's Retry-After interval.
            retry_after = response.headers.get("Retry-After", "unspecified")
            raise ValueError(f"AIHOT HTTP {response.status_code}; Retry-After={retry_after}")
        cache_control = response.headers.get("Cache-Control", "")
        if "no-store" in cache_control:
            try:
                self.cache_path.unlink(missing_ok=True)
            except OSError:
                pass
            return payload
        max_age = re.search(r"(?:^|,)\s*max-age=(\d+)", cache_control)
        ttl = int(max_age[1]) if max_age else 60
        if "no-cache" in cache_control:
            ttl = 0
        etag = response.headers.get("ETag")
        if response.status_code == 304 and etag is None:
            etag = cache.get("etag")
        record = {"url": self.url, "etag": etag,
                  "expires_at": now + min(ttl, 300), "payload": payload}
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.cache_path.parent, delete=False) as handle:
                json.dump(record, handle, ensure_ascii=False)
            Path(handle.name).replace(self.cache_path)
        except OSError:
            pass  # A cache write failure must not discard a valid API response.
        return payload

    def fetch(self, context):
        if context.historical:
            return SourceResult(self.name, SourceStatus.SKIPPED, error="historical retrieval is unavailable for AIHOT")
        try:
            entries = []
            for raw in self._payload()["items"]:
                if not isinstance(raw, dict):
                    continue
                links = raw.get("links") or {}
                if not isinstance(links, dict) or not isinstance(raw.get("title"), str):
                    continue
                url = links.get("aihot", "")
                if not isinstance(url, str):
                    continue
                parsed = urlsplit(url)
                if parsed.scheme != "https" or parsed.netloc != "aihot.news":
                    continue
                if not isinstance(raw.get("summary"), str) or not raw["summary"].strip():
                    continue
                original = links.get("original")
                if original and isinstance(original, str):
                    original_parts = urlsplit(original)
                    if (
                        original_parts.scheme not in {"http", "https"}
                        or not original_parts.hostname
                        or original_parts.username or original_parts.password
                    ):
                        original = None
                else:
                    original = None
                upstream = raw.get("source")
                entries.append({
                    "title": raw.get("title"), "url": url, "summary": raw["summary"],
                    "published_at": raw.get("publishedAt"),
                    "metadata": {
                        "aihot_id": raw.get("id"), "aihot_url": url, "original_url": original,
                        "aihot_category": raw.get("category"), "aihot_score": raw.get("score"),
                        "provider_source": upstream.get("name") if isinstance(upstream, dict) else None,
                        "discovered_at": raw.get("discoveredAt"), "attribution": raw.get("attribution"),
                        "material_kind": "provider_summary", "requires_attribution": True,
                    },
                })
            result = SourceResult.from_dicts(self.name, SourceTier.AGGREGATOR, entries)
            result.items = prioritize_items(result.items, self.profile)[:context.limit]
            return result
        except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
            return SourceResult(self.name, SourceStatus.FAILED, error=f"AIHOT retrieval failed: {type(error).__name__}: {error}"[:240])
