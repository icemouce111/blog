"""Automatic evidence validation and fail-soft report repair."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Callable, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scripts.ai_daily_sources import (
    SourceItem,
    SourceResult,
    SourceTier,
)


URL_PATTERN = re.compile(r"https?://[^\s<>\])]+")
ATTRIBUTION_MARKERS = (
    "据",
    "社区",
    "用户",
    "开发者",
    "讨论",
    "帖子",
    "分享",
    "指出",
)
RESTRICTED_CLAIMS = (
    "最快",
    "全球第一",
    "行业第一",
    "明确的蓝海",
    "明确蓝海",
    "我断言",
    "我锁定",
    "必然成为",
    "唯一选择",
)


class QualityMode(str, Enum):
    ORIGINAL = "original"
    REPAIRED = "repaired"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[str, ...]


@dataclass(frozen=True)
class QualityResult:
    content: str
    mode: QualityMode
    issues: tuple[str, ...]


def filter_usable_items(
    items: Iterable[SourceItem],
    target_date: date,
    *,
    max_age_days: int = 45,
) -> list[SourceItem]:
    usable = []
    earliest = target_date - timedelta(days=max_age_days)
    latest = target_date + timedelta(days=1)
    for item in items:
        if not item.title.strip() or not _valid_http_url(item.url):
            continue
        published = _date_part(item.published_at)
        if published and not earliest <= published <= latest:
            continue
        usable.append(item)
    return usable


def validate_report(
    content: str,
    evidence: Iterable[SourceItem],
) -> ValidationResult:
    items = list(evidence)
    issues = []
    if not re.search(r"^##\s+\d{2}\b", content, flags=re.MULTILINE):
        issues.append("report has no numbered sections")

    allowed = {_canonical_url(item.url): item for item in items}
    for url in _extract_urls(content):
        key = _canonical_url(url)
        if key not in allowed:
            issues.append(f"report URL is not in collected evidence: {url}")

    for block in re.split(r"\n\s*\n", content):
        community_urls = [
            url
            for url in _extract_urls(block)
            if (
                _canonical_url(url) in allowed
                and allowed[_canonical_url(url)].source_tier
                == SourceTier.COMMUNITY
            )
        ]
        if community_urls and not any(
            marker in block for marker in ATTRIBUTION_MARKERS
        ):
            issues.append(
                "community-only claim lacks attribution: "
                + community_urls[0]
            )

    evidence_text = "\n".join(
        f"{item.title}\n{item.summary}" for item in items
    )
    for phrase in RESTRICTED_CLAIMS:
        if phrase in content and phrase not in evidence_text:
            issues.append(
                f"unsupported absolute or promotional claim: {phrase}"
            )

    return ValidationResult(not issues, tuple(issues))


def validate_repair_or_fallback(
    content: str,
    results: Mapping[str, SourceResult],
    *,
    target_date: date,
    repair: Callable[[str], str | None] | None,
) -> QualityResult:
    items = _usable_from_results(results, target_date)
    initial = validate_report(content, items)
    if initial.valid:
        return QualityResult(content, QualityMode.ORIGINAL, ())

    if repair is not None:
        repaired = repair(_repair_prompt(content, initial.issues, items))
        if repaired:
            repaired_validation = validate_report(repaired, items)
            if repaired_validation.valid:
                return QualityResult(
                    repaired,
                    QualityMode.REPAIRED,
                    initial.issues,
                )

    fallback = build_signal_fallback(results, target_date=target_date)
    return QualityResult(fallback, QualityMode.FALLBACK, initial.issues)


def build_signal_fallback(
    results: Mapping[str, SourceResult],
    *,
    target_date: date,
) -> str:
    parts = ["## 01 📡 原始信号归档", ""]
    for source, result in results.items():
        items = filter_usable_items(result.items, target_date)
        if not items:
            continue
        parts.append(f"### {source}")
        for item in items[:8]:
            if item.source_tier == SourceTier.COMMUNITY:
                lead = f"据 {source} 社区：{item.title}"
            else:
                lead = item.title
            line = f"- **{lead}**"
            if item.summary:
                line += f"：{_compact(item.summary, 160)}"
            line += f" [来源]({item.url})"
            parts.append(line)
        parts.append("")
    if len(parts) == 2:
        parts.extend([
            "### 系统状态",
            "- 今日没有通过自动质量检查的有效数据。",
        ])
    return "\n".join(parts).strip()


def _usable_from_results(
    results: Mapping[str, SourceResult],
    target_date: date,
) -> list[SourceItem]:
    return [
        item
        for result in results.values()
        for item in filter_usable_items(result.items, target_date)
    ]


def _repair_prompt(
    content: str,
    issues: Iterable[str],
    items: Iterable[SourceItem],
) -> str:
    evidence_lines = [
        f"- [{item.source_tier.value}] {item.source}: "
        f"{item.title} | {item.url} | {item.summary}"
        for item in items
    ]
    return f"""修复下面的 AI 日报正文。只允许使用证据清单中的事实和 URL。

要求：
- 保留 `## NN` 编号栏目结构。
- 社区来源必须明确写成“据社区讨论”或“有用户/开发者指出”。
- 删除证据不支持的最快、第一、唯一、蓝海和确定性预测。
- 不得添加证据清单之外的 URL。
- 只输出修复后的 Markdown 正文。

检测到的问题：
{chr(10).join(f"- {issue}" for issue in issues)}

证据清单：
{chr(10).join(evidence_lines)}

待修复正文：
{content}
"""


def _extract_urls(content: str) -> list[str]:
    return [
        match.group(0).rstrip(".,;:，。；：")
        for match in URL_PATTERN.finditer(content)
    ]


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


def _date_part(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _compact(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
