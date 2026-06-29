"""Build guarded week/month/year AI application trend snapshots from daily archives."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


WINDOWS = {
    "week": {"days": 7, "minimum": 4, "cadence_days": 1},
    "month": {"days": 30, "minimum": 14, "cadence_days": 7},
    "year": {"days": 365, "minimum": 60, "cadence_days": 30},
}

URL_PATTERN = re.compile(r"https?://[^\s)>\]]+")
CST = timezone(timedelta(hours=8), "Asia/Shanghai")


def should_refresh(window, coverage_count, age_days):
    config = WINDOWS[window]
    return (
        coverage_count >= config["minimum"]
        and age_days >= config["cadence_days"]
    )


def validate_insight_sources(insight, allowed_urls):
    sources = insight.get("sources") if isinstance(insight, dict) else None
    return (
        isinstance(sources, list)
        and len(sources) > 0
        and all(
            isinstance(source, dict)
            and isinstance(source.get("title"), str)
            and source["title"].strip()
            and source.get("url") in allowed_urls
            for source in sources
        )
    )


def _issue_date(path):
    try:
        return datetime.strptime(path.stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def select_issues(content_dir, days, today=None):
    today = today or datetime.now(CST).date()
    start = today - timedelta(days=days - 1)
    selected = []
    for path in Path(content_dir).glob("????-??-??.md"):
        issue_date = _issue_date(path)
        if issue_date and start <= issue_date <= today:
            selected.append((issue_date, path))
    return sorted(selected, reverse=True)


def extract_source_dates(issues):
    source_dates = {}
    for issue_date, path in issues:
        content = path.read_text(encoding="utf-8")
        for url in URL_PATTERN.findall(content):
            clean_url = url.rstrip(".,;:")
            source_dates.setdefault(clean_url, issue_date.isoformat())
    return source_dates


def build_prompt(window, issues, allowed_urls):
    excerpts = []
    for issue_date, path in issues:
        content = path.read_text(encoding="utf-8")
        excerpts.append(f"### {issue_date.isoformat()}\n{content[-12000:]}")

    return f"""你是中文 AI 行业编辑。请从以下 {len(issues)} 期日报中归纳“{window}”范围内的全球 AI 应用趋势。

只输出 JSON，不要 Markdown 代码块，格式必须是：
{{"insights":[{{"title":"不超过24字","summary":"80至140字，说明应用层变化与影响","sources":[{{"title":"来源标题","url":"完整URL"}}]}}]}}

硬性要求：
- 恰好 3 条洞察，聚焦真实应用、工作流、组织采用或垂直行业，不复述单条新闻。
- 每条至少 1 个来源；URL 只能逐字选自下方允许列表，不得创造或改写。
- 不得加入日报中没有依据的数字、公司或结论。

允许 URL：
{json.dumps(sorted(allowed_urls), ensure_ascii=False)}

日报材料：
{"\n\n".join(excerpts)}
"""


def _parse_llm_json(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _validated_insights(raw, source_dates):
    parsed = _parse_llm_json(raw)
    insights = parsed.get("insights") if isinstance(parsed, dict) else None
    if not isinstance(insights, list) or len(insights) != 3:
        return None

    normalized = []
    allowed_urls = set(source_dates)
    for insight in insights:
        if (
            not isinstance(insight, dict)
            or not isinstance(insight.get("title"), str)
            or not insight["title"].strip()
            or not isinstance(insight.get("summary"), str)
            or not insight["summary"].strip()
            or not validate_insight_sources(insight, allowed_urls)
        ):
            return None
        normalized.append({
            "title": insight["title"].strip(),
            "summary": insight["summary"].strip(),
            "sources": [{
                "title": source["title"].strip(),
                "url": source["url"],
                "publishedAt": source_dates[source["url"]],
            } for source in insight["sources"]],
        })
    return normalized


def _snapshot_age_days(snapshot, today):
    if not isinstance(snapshot, dict):
        return 10**6
    try:
        updated = datetime.fromisoformat(snapshot["updatedAt"]).date()
    except (KeyError, TypeError, ValueError):
        return 10**6
    return max(0, (today - updated).days)


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def refresh_trends(
    content_dir,
    snapshot_path,
    llm_call: Callable[[str], str | None],
    now=None,
):
    """Refresh eligible windows and preserve every window that fails validation."""
    now = now or datetime.now(CST)
    today = now.date()
    snapshot_path = Path(snapshot_path)
    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"windows": []}

    existing = {
        item.get("window"): item
        for item in data.get("windows", [])
        if isinstance(item, dict) and item.get("window") in WINDOWS
    }
    changed = False

    for window, config in WINDOWS.items():
        issues = select_issues(content_dir, config["days"], today)
        age_days = _snapshot_age_days(existing.get(window), today)
        if not should_refresh(window, len(issues), age_days):
            continue

        source_dates = extract_source_dates(issues)
        if not source_dates:
            continue

        try:
            raw = llm_call(build_prompt(window, issues, set(source_dates)))
        except Exception as error:
            print(f"  [warn] Trend refresh {window} failed: {error}")
            continue
        insights = _validated_insights(raw, source_dates)
        if not insights:
            print(f"  [warn] Trend refresh {window} rejected invalid output")
            continue

        existing[window] = {
            "window": window,
            "rangeStart": issues[-1][0].isoformat(),
            "rangeEnd": issues[0][0].isoformat(),
            "updatedAt": now.isoformat(timespec="seconds"),
            "coverageCount": len(issues),
            "mode": "generated",
            "insights": insights,
        }
        changed = True

    if changed:
        ordered = [existing[window] for window in WINDOWS if window in existing]
        _atomic_write_json(snapshot_path, {"windows": ordered})
    return changed
