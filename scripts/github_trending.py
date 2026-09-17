"""GitHub Trending fetcher and defensive HTML parser for GitHub Daily."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup, Tag

TRENDING_URL = "https://github.com/trending"
RAW_README_URL = "https://raw.githubusercontent.com/{full_name}/{branch}/README.md"
README_BRANCHES = ("HEAD", "main", "master")
README_MAX_CHARS = 6000
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_REPO_HREF_PATTERN = re.compile(r"^/([^/\s#]+)/([^/\s#]+)/?$")
# first path segments that can never be "owner" of a repository
_NON_REPO_SEGMENTS = {
    "about",
    "collections",
    "explore",
    "features",
    "join",
    "login",
    "notifications",
    "orgs",
    "pricing",
    "security",
    "settings",
    "site",
    "sponsors",
    "topics",
    "trending",
}


class TrendingFetchError(RuntimeError):
    """Raised when the trending page cannot be fetched or yields no repos."""


@dataclass
class TrendingRepo:
    rank: int
    full_name: str
    url: str
    description: str = ""
    language: str = ""
    stars: int | None = None
    forks: int | None = None
    stars_today: int | None = None
    topics: list[str] = field(default_factory=list)


def parse_count(text: str | None) -> int | None:
    """Parse "1,234" style counters; return None when no number present."""
    if not text:
        return None
    match = re.search(r"\d[\d,]*", text)
    if not match:
        return None
    return int(match.group(0).replace(",", ""))


def _normalize_href(raw: str | None) -> str | None:
    href = (raw or "").strip()
    if href.startswith("http"):
        match = re.search(r"github\.com(/[^?\s#]+)", href)
        if not match:
            return None
        href = match.group(1)
    if not href.startswith("/"):
        return None
    parts = [part for part in href.split("/") if part]
    if len(parts) != 2:
        return None
    if parts[0].lower() in _NON_REPO_SEGMENTS:
        return None
    return f"{parts[0]}/{parts[1]}"


def _extract_full_name(row: Tag) -> str | None:
    heading_link = row.select_one("h2 a[href]")
    if heading_link is not None:
        normalized = _normalize_href(heading_link.get("href"))
        if normalized:
            return normalized
    for anchor in row.select("a[href]"):
        normalized = _normalize_href(anchor.get("href"))
        if normalized:
            return normalized
    return None


def _extract_stars_today(row: Tag) -> int | None:
    for span in row.find_all("span"):
        text = span.get_text(" ", strip=True)
        match = re.search(r"([\d,]+)\s+stars?\s+today", text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def parse_trending_html(html: str, *, limit: int = 15) -> list[TrendingRepo]:
    """Defensively parse the trending page; skip rows we cannot understand."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("article.Box-row") or soup.select("article")
    repos: list[TrendingRepo] = []
    seen: set[str] = set()

    for row in rows:
        if len(repos) >= limit:
            break
        full_name = _extract_full_name(row)
        if not full_name or full_name in seen:
            continue
        seen.add(full_name)

        description_el = row.select_one("p")
        language_el = row.select_one('[itemprop="programmingLanguage"]')
        stars_el = row.select_one('a[href$="/stargazers"]')
        forks_el = row.select_one('a[href$="/forks"], a[href$="/network/members"]')
        topics = [a.get_text(strip=True) for a in row.select("a.topic-tag")]

        repos.append(
            TrendingRepo(
                rank=len(repos) + 1,
                full_name=full_name,
                url=f"https://github.com/{full_name}",
                description=(
                    description_el.get_text(" ", strip=True)
                    if description_el is not None
                    else ""
                ),
                language=(
                    language_el.get_text(strip=True)
                    if language_el is not None
                    else ""
                ),
                stars=(
                    parse_count(stars_el.get_text(" ", strip=True))
                    if stars_el is not None
                    else None
                ),
                forks=(
                    parse_count(forks_el.get_text(" ", strip=True))
                    if forks_el is not None
                    else None
                ),
                stars_today=_extract_stars_today(row),
                topics=topics,
            )
        )
    return repos


def rank_repos_by_daily_stars(repos: list[TrendingRepo]) -> list[TrendingRepo]:
    """Return the Trending candidates ranked by their reported daily Star gain."""
    ranked = sorted(
        repos,
        key=lambda repo: (
            repo.stars_today is None,
            -(repo.stars_today or 0),
            repo.full_name.lower(),
        ),
    )
    return [replace(repo, rank=index) for index, repo in enumerate(ranked, start=1)]


def _curl_fetch_html(url: str) -> str:
    """Fetch a URL via the curl binary.

    curl has proven resilient when Python's HTTP stack (requests/urllib) is
    blocked by GitHub's intermittent client-side throttling (read-timeout on
    responses even though TCP/TLS handshakes succeed).
    """
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "--fail",
            "--max-time",
            "45",
            "-A",
            USER_AGENT,
            url,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise TrendingFetchError(
            f"curl fallback failed for {url}: "
            f"exit={result.returncode} {result.stderr.strip()[:200]}"
        )
    return result.stdout


def fetch_trending(
    *,
    limit: int = 15,
    since: str = "daily",
    language: str | None = None,
) -> list[TrendingRepo]:
    params: dict[str, str] = {"since": since}
    if language:
        params["language"] = language
    url = f"{TRENDING_URL}?{urlencode(params)}"
    html: str | None = None
    try:
        response = requests.get(
            url,
            params=None,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if response.status_code == 200:
            html = response.text
    except requests.RequestException:
        pass  # fall through to curl fallback
    if html is None:
        html = _curl_fetch_html(url)
    repos = parse_trending_html(html, limit=limit)
    if not repos:
        raise TrendingFetchError(
            "parsed zero repositories from trending page "
            "(markup may have changed)"
        )
    return rank_repos_by_daily_stars(repos)


def repo_to_payload(repo: TrendingRepo) -> dict[str, Any]:
    return {
        "rank": repo.rank,
        "fullName": repo.full_name,
        "url": repo.url,
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "starsToday": repo.stars_today,
        "forks": repo.forks,
        "topics": repo.topics,
    }


def _clean_readme(text: str) -> str:
    """Strip badge noise and over-long markup so the LLM sees substance."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # badge shields / image-only lines / html comments / anchor jumps
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith(("[![", "<!--", "<div", "</div", "<p ", "</p", "<img")):
            continue
        if stripped.startswith("[") and "](" in stripped and stripped.count("(") <= 3 and len(stripped) < 200 and "http" in stripped and stripped.rstrip().endswith(")"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned[:README_MAX_CHARS]


def fetch_readme(full_name: str, *, timeout: int = 15) -> str:
    """Fetch the repo README via raw.githubusercontent (no API rate limit).

    Tries HEAD then main then master; returns '' when none resolve — the
    caller treats empty as 'no readme', never as a fatal error.
    """
    headers = {"User-Agent": USER_AGENT}
    for branch in README_BRANCHES:
        url = RAW_README_URL.format(full_name=full_name, branch=branch)
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except requests.RequestException:
            continue
        if response.status_code == 200 and response.text.strip():
            return _clean_readme(response.text)
        if response.status_code == 404:
            continue
        # 4xx other than 404: don't hammer remaining branches
        if 400 <= response.status_code < 500:
            break
    return ""
