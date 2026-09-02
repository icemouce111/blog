#!/usr/bin/env python3
"""
AI 日报生成器 — 每日自动抓取与分析

使用方式:
  python3 scripts/generate-ai-daily.py

依赖: scripts/requirements.txt

流程:
  1. 并行抓取注册的数据源
  2. LLM 多角色分析师 (7 个角色) 分析
  3. 自动质量控制并生成 markdown
  4. 从 origin/main 隔离提交并推送
  5. 验证远端 SHA 与 Cloudflare RSS

环境变量:
  DEEPSEEK_API_KEY (推荐) or OPENAI_API_KEY — LLM 调用
  X_BEARER_TOKEN — X 官方 recent search API（可选）
  XIAOHONGSHU_API_BASE — 小红书 MCP 地址（可选）
"""

import argparse
import json
import os
import subprocess
import sys
import traceback
import ssl
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

try:
    from scripts.ai_daily_quality import (
        QualityMode,
        filter_usable_items,
        validate_repair_or_fallback,
    )
    from scripts.ai_daily_sop import Publisher
    from scripts.ai_daily_sources import (
        AnthropicNewsSource,
        CallableSource,
        LinuxDoSource,
        OpenAINewsSource,
        OfficialRssSource,
        RedditSource,
        SourceContext,
        SourceRegistry,
        SourceStatus,
        SourceTier,
        XiaohongshuSource,
        XSource,
    )
except ModuleNotFoundError:
    from ai_daily_quality import (
        QualityMode,
        filter_usable_items,
        validate_repair_or_fallback,
    )
    from ai_daily_sop import Publisher
    from ai_daily_sources import (
        AnthropicNewsSource,
        CallableSource,
        LinuxDoSource,
        OpenAINewsSource,
        OfficialRssSource,
        RedditSource,
        SourceContext,
        SourceRegistry,
        SourceStatus,
        SourceTier,
        XiaohongshuSource,
        XSource,
    )
try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

BLOG_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BLOG_DIR / "src" / "content" / "ai-daily"
CST = timezone(timedelta(hours=8), "Asia/Shanghai")


# ── .env 加载 ──────────────────────────
def _load_env():
    """从 .env 文件加载环境变量（纯 Python，零依赖）"""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("\"'\"")
            if key and value:
                os.environ.setdefault(key, value)

_load_env()

# ── LLM 配置 ──────────────────────────
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
_use_deepseek = bool(os.environ.get("DEEPSEEK_API_KEY"))
LLM_BASE_URL = "https://api.deepseek.com/v1" if _use_deepseek else "https://api.openai.com/v1"
LLM_MODEL = "deepseek-chat" if _use_deepseek else "gpt-4o"


# ── 工具函数 ──────────────────────────

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate and publish AI Daily")
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate validated artifacts without Git publication",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch, analyze and validate without writing files or publishing",
    )
    parser.add_argument(
        "--date",
        help="Target date in YYYY-MM-DD format (defaults to today in CST)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing report for the target date",
    )
    args = parser.parse_args(argv)
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            parser.error("--date must use YYYY-MM-DD")
    return args

def _fetch(url, headers=None, timeout=30):
    req = Request(url, headers=headers or {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except HTTPError as e:
        print(f"    [fail] {url[:70]}... -> HTTP {e.code}")
        return None
    except URLError as e:
        if "SSL" in str(e):
            try:
                ctx = ssl._create_unverified_context()
                with urlopen(req, timeout=timeout, context=ctx) as resp:
                    return resp.read()
            except Exception:
                pass
        print(f"    [fail] {url[:70]}... -> {e.reason}")
        return None
    except Exception as e:
        print(f"    [fail] {url[:70]}... -> {e}")
        return None


def _fetch_json(url, headers=None):
    data = _fetch(url, headers)
    if data is None:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def _safe_parse_browser_json(text):
    """Robust JSON parsing for bb-browser output that may be truncated mid-string.

    bb-browser can produce unterminated JSON when a tweet text is very
    long and gets truncated. Tries multiple recovery strategies.
    """
    if not text:
        return None

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip non-JSON control characters
    _cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    try:
        return json.loads(_cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: raw_decode finds longest valid JSON prefix
    _decoder = json.JSONDecoder()
    try:
        _obj, _ = _decoder.raw_decode(text)
        return _obj
    except json.JSONDecodeError:
        pass
    try:
        _obj, _ = _decoder.raw_decode(_cleaned)
        return _obj
    except json.JSONDecodeError:
        pass

    # Strategy 4: Try to close unterminated string + remaining structure
    for _closer in ['"}]}}', '"}']:
        try:
            return json.loads(text.rstrip() + _closer)
        except json.JSONDecodeError:
            continue

    return None




# -- 垃圾信息过滤规则 ------------------
_GITHUB_SPAM_RE = re.compile(
    r'(crack|keygen|activator|mod\s*jar|'
    r'cheat|hack|spoofer|exploit|panel|'
    r'license\s*key|pre.?activated|lifetime\s*(license|activation)|'
    r'fortnite|mega\s*nuker|discord\s*nitro|steam\s*unlocker|'
    r'idm\s*(manager|activator|crack)|lossless.?scaling|'
    r'bypass|unban|account\s*creator)',
    re.IGNORECASE
)

def _is_github_spam(name, description):
    desc = f"{name} {description or ''}"
    return bool(_GITHUB_SPAM_RE.search(desc))

_BILIBILI_SCAM_RE = re.compile(
    r'(清华大佬|全套|速成|零基础|白嫖|'
    r'学不会我|拿走不谢|允许白嫖|看完少走|'
    r'告别盲目自学|少走99|全部学会|'
    r'一学就会|从入门到放弃|轻松玩转)',
    flags=re.IGNORECASE
)

def _is_bilibili_scam(title):
    return bool(_BILIBILI_SCAM_RE.search(title or ""))

_TECH_KEYWORDS = re.compile(
    r'(AI|人工智能|machine learning|deep learning|LLM|大模型|agent|'
    r'MCP|GPT|Claude|Codex|Copilot|Cursor|Windsurf|'
    r'open source|开源|模型|算法|编程|代码|'
    r'developer|framework|library|SDK|API|'
    r'GPU|CPU|token|训练|推理|部署|'
    r'融资|funding|收购|acquisition|regulation|政策|'
    r'startup|创业|技术|programming|software)',
    flags=re.IGNORECASE
)

def _is_tech_related(title, description=""):
    text = f"{title or ''} {description or ''}"
    return bool(_TECH_KEYWORDS.search(text))


_PERSONAL_INTEREST_KEYWORDS = re.compile(
    r'(agent|agentic|skill|MCP|RAG|context|memory|eval|workflow|automation|'
    r'Claude Code|Codex|AI coding|coding agent|developer tool|TypeScript|React|'
    r'Cloudflare|enterprise AI|AI office|productivity|document|spreadsheet|'
    r'knowledge base|customer support|creator|tutorial|education|'
    r'智能体|工作流|上下文|记忆|评测|编程|开发工具|企业 AI|办公|'
    r'文档|表格|知识库|客服|创作者|教程|教学|小白|豆包|千问|Kimi)',
    flags=re.IGNORECASE,
)


def _is_personal_interest_related(title, description=""):
    return bool(_PERSONAL_INTEREST_KEYWORDS.search(f"{title or ''} {description or ''}"))

# ── 数据源抓取 ────────────────────────
def fetch_hackernews(n=12, *, target_date=None):
    """Hacker News Top Stories (Firebase API)"""
    print("  Fetching Hacker News...")
    if target_date:
        start = datetime.combine(target_date, datetime.min.time(), tzinfo=CST)
        end = start + timedelta(days=1)
        query = urlencode({
            "tags": "story",
            "numericFilters": (
                f"created_at_i>={int(start.timestamp())},"
                f"created_at_i<{int(end.timestamp())}"
            ),
            "hitsPerPage": n,
        })
        data = _fetch_json(
            f"https://hn.algolia.com/api/v1/search_by_date?{query}"
        )
        stories = []
        for item in (data or {}).get("hits", []):
            title = item.get("title") or item.get("story_title")
            if not title:
                continue
            story_id = item.get("objectID")
            story = {
                "title": title,
                "url": item.get("url")
                or f"https://news.ycombinator.com/item?id={story_id}",
                "score": item.get("points", 0),
                "by": item.get("author", ""),
                "published_at": item.get("created_at"),
            }
            if _is_personal_interest_related(title):
                stories.append(story)
        return stories[:n]

    ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids:
        return []
    stories = []
    for sid in ids[: n * 4]:
        item = _fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if item and item.get("title") and _is_personal_interest_related(item["title"]):
            stories.append({
                "title": item["title"],
                "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                "score": item.get("score", 0),
                "by": item.get("by", ""),
                "published_at": (
                    datetime.fromtimestamp(item["time"], timezone.utc).isoformat()
                    if item.get("time")
                    else None
                ),
            })
        if len(stories) >= n:
            break
    return stories


def _parse_github_trending_html(text):
    """Parse GitHub Trending HTML and return repo list (spam-filtered)"""
    repos = []
    _bs4 = None
    try:
        from bs4 import BeautifulSoup as _bs4
    except ImportError:
        pass

    if _bs4:
        soup = _bs4(text, "html.parser")
        for article in soup.select("article"):
            h2 = article.find("h2")
            if not h2:
                continue
            a_tag = h2.find("a")
            if not a_tag:
                continue
            href = a_tag.get("href", "").strip("/")
            if "/" not in href:
                continue
            owner, name_part = href.split("/", 1)
            desc_p = article.find("p")
            desc = desc_p.get_text(strip=True) if desc_p else ""
            lang_span = article.select_one('span[itemprop="programmingLanguage"]')
            language = lang_span.get_text(strip=True) if lang_span else ""
            stars = 0
            for svg in article.select("svg.octicon-star"):
                parent = svg.parent
                if parent:
                    star_text = parent.get_text(strip=True).replace(",", "")
                    match = re.match(r"(\d+(?:\.\d+)?)(k)?", star_text)
                    if match:
                        val = float(match.group(1))
                        stars = int(val * 1000) if match.group(2) else int(val)
                    break
            repo = {
                "name": f"{owner}/{name_part}",
                "description": desc[:200],
                "url": f"https://github.com/{owner}/{name_part}",
                "language": language,
                "stars": stars,
            }
            if not _is_github_spam(repo["name"], repo["description"]):
                repos.append(repo)
    else:
        for article in text.split("<article")[1:]:
            h2_match = re.search(r"<h2[^>]*>(.*?)</h2>", article, re.DOTALL)
            if not h2_match:
                continue
            h2_html = h2_match.group(1)
            a_match = re.search(r'href\s*=\s*"([^"]*)"', h2_html)
            if not a_match:
                continue
            href = a_match.group(1).strip("/")
            parts = href.split("/")
            if len(parts) < 2:
                continue
            owner, name_part = parts[0], parts[1]
            desc_match = re.search(r"<p[^>]*>(.*?)</p>", article, re.DOTALL)
            desc = ""
            if desc_match:
                desc = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()[:200]
            lang_match = re.search(r'itemprop="programmingLanguage"[^>]*>([^<]+)', article)
            language = lang_match.group(1).strip() if lang_match else ""
            repo = {
                "name": f"{owner}/{name_part}",
                "description": desc[:200],
                "url": f"https://github.com/{owner}/{name_part}",
                "language": language,
                "stars": 0,
            }
            if not _is_github_spam(repo["name"], repo["description"]):
                repos.append(repo)
    return repos

def fetch_github_trending(*, target_date=None):
    """GitHub Trending: HTML trending page first, API fallback with spam filter"""
    print("  Fetching GitHub Trending...")
    if target_date:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        query = urlencode({
            "q": f"created:{target_date.isoformat()} stars:>0",
            "sort": "stars",
            "order": "desc",
            "per_page": 10,
        })
        data = _fetch_json(
            f"https://api.github.com/search/repositories?{query}",
            headers,
        )
        repos = []
        for repo_data in (data or {}).get("items", []):
            repo = {
                "name": repo_data["full_name"],
                "description": repo_data.get("description") or "",
                "stars": repo_data.get("stargazers_count", 0),
                "url": repo_data["html_url"],
                "language": repo_data.get("language") or "",
                "published_at": repo_data.get("created_at"),
            }
            if not _is_github_spam(repo["name"], repo["description"]):
                repos.append(repo)
        return repos[:10]

    # Strategy 1: HTML trending page (best signal quality)
    html = _fetch("https://github.com/trending")
    if html:
        repos = _parse_github_trending_html(html.decode("utf-8", errors="replace"))
        if repos:
            return repos[:10]
        print("    [warn] Trending page empty or all spam, falling back to API")
    # Strategy 2: GitHub Search API with stars>50 + spam filter
    print("    [info] Using GitHub Search API...")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    yesterday = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = _fetch_json(
        f"https://api.github.com/search/repositories?q=created:>={yesterday}+stars:>50&sort=stars&order=desc&per_page=10",
        headers,
    )
    if data and "items" in data:
        repos = []
        for r in data["items"]:
            repo = {
                "name": r["full_name"],
                "description": r.get("description") or "",
                "stars": r.get("stargazers_count", 0),
                "url": r["html_url"],
                "language": r.get("language") or "",
                "published_at": r.get("created_at"),
            }
            if not _is_github_spam(repo["name"], repo["description"]):
                repos.append(repo)
        return repos[:10]
    return []





def fetch_v2ex():
    """V2EX 最热主题"""
    print("  Fetching V2EX...")
    data = _fetch_json("https://www.v2ex.com/api/topics/hot.json")
    if not data:
        return []
    results = []
    for t in data:
        title = t.get("title", "")
        node_title = t.get("node", {}).get("title", "")
        if _is_tech_related(title, node_title):
            results.append({
                "title": title,
                "url": f"https://www.v2ex.com/t/{t.get('id', '')}",
                "node": node_title,
                "replies": t.get("replies", 0),
            })
        if len(results) >= 8:
            break
    return results


def fetch_huggingface(*, target_date=None):
    """HuggingFace Daily Papers"""
    print("  Fetching HuggingFace Papers...")
    endpoint = "https://huggingface.co/api/daily_papers"
    if target_date:
        endpoint += f"?date={target_date.isoformat()}"
    data = _fetch_json(endpoint)
    if not data:
        return []
    results = []
    candidates = []
    for p in data[:20]:
        # Paper ID is nested under "paper" key in HF API response
        paper_obj = p.get("paper") or {}
        paper_id = paper_obj.get("id") or p.get("id", "")
        if not paper_id:
            paper_url = paper_obj.get("url") or p.get("paperUrl", "") or p.get("url", "")
            if paper_url:
                paper_id = paper_url.rstrip("/").rsplit("/", 1)[-1] if "/" in paper_url else ""
        url = f"https://huggingface.co/papers/{paper_id}" if paper_id else (paper_obj.get("url") or p.get("url", ""))
        record = {
            "title": paper_obj.get("title") or p.get("title", ""),
            "url": url,
            "upvotes": p.get("upvotes", 0),
            "summary": (paper_obj.get("summary") or p.get("summary") or "")[:200],
            # The endpoint itself is a day-specific curation archive. Its
            # paper publication timestamp can predate the daily selection.
            "published_at": (
                target_date.isoformat()
                if target_date
                else p.get("publishedAt") or paper_obj.get("publishedAt")
            ),
            "metadata": (
                {"daily_papers_date": target_date.isoformat()}
                if target_date
                else {}
            ),
        }
        if _is_personal_interest_related(record["title"], record["summary"]):
            results.append(record)
        candidates.append(record)
    return (results or candidates[:3])[:10]


def fetch_producthunt():
    """Product Hunt 新品 (RSS)"""
    print("  Fetching Product Hunt...")
    xml_data = _fetch("https://www.producthunt.com/feed?category=tech")
    if not xml_data:
        return []
    try:
        root = ElementTree.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            summary_el = entry.find("atom:summary", ns)
            summary = ""
            if summary_el is not None and summary_el.text:
                summary = re.sub(r"<[^>]+>", "", summary_el.text)[:200]
            if not summary:
                content_el = entry.find("atom:content", ns)
                if content_el is not None and content_el.text:
                    summary = re.sub(r"<[^>]+>", "", content_el.text)[:200]
            item = {
                "title": title_el.text if title_el is not None else "",
                "url": link_el.get("href") if link_el is not None else "",
                "description": summary,
            }
            if _is_personal_interest_related(item["title"], item["description"]):
                items.append(item)
        return items[:8]
    except Exception:
        return []


def fetch_reddit():
    """Reddit 热门帖子 (通过 bb-browser)"""
    print("  Fetching Reddit...")
    subreddits = ["MachineLearning", "LocalLLaMA", "ClaudeCode", "OpenAI", "ArtificialIntelligence"]
    results = []
    for sub in subreddits:
        try:
            r = subprocess.run(
                ["bb-browser", "site", "reddit/hot", sub, "--json"],
                capture_output=True, text=True, timeout=20
            )
            if r.returncode == 0 and r.stdout.strip():
                data = _safe_parse_browser_json(r.stdout)
                if data is None:
                    print(f"    [skip] bb-browser reddit/{sub}: JSON parse failed")
                    continue
                posts = data.get("result", {}).get("posts", [])
                for item in (posts[:5] if isinstance(posts, list) else [posts]):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", item.get("permalink", "")),
                        "score": item.get("score", 0),
                        "comments": item.get("num_comments", item.get("commentCount", 0)),
                        "subreddit": item.get("subreddit", sub),
                    })
        except FileNotFoundError:
            print("    [skip] bb-browser not installed")
            return []
        except subprocess.TimeoutExpired:
            print(f"    [skip] bb-browser reddit/{sub} timeout")
            continue
        except Exception as e:
            print(f"    [skip] bb-browser reddit/{sub}: {str(e)[:40]}")
            continue
    return sorted(results, key=lambda x: x["score"], reverse=True)[:10]


def fetch_x_twitter():
    """X/Twitter AI 社区动态 (通过 bb-browser)"""
    print("  Fetching X/Twitter...")
    results = []
    queries = [
        "AI agent skills MCP workflow",
        "Claude Code Codex AI coding",
        "AI office 豆包 Qwen Kimi creator",
    ]
    for query in queries:
        try:
            r = subprocess.run(
                ["bb-browser", "site", "twitter/search", query, "--json"],
                capture_output=True, text=True, timeout=20
            )
            if r.returncode == 0 and r.stdout.strip():
                data = _safe_parse_browser_json(r.stdout)
                if data is None:
                    print("    [skip] bb-browser twitter/query: JSON parse failed")
                    continue
                tweets = data.get("result", {}).get("tweets", [])
                for item in (tweets[:7] if isinstance(tweets, list) else [tweets]):
                    results.append({
                        "title": item.get("text", ""),
                        "url": item.get("url", ""),
                        "author": item.get("author", ""),
                        "likes": item.get("likes", 0),
                        "retweets": item.get("retweets", 0),
                    })
        except FileNotFoundError:
            print("    [skip] bb-browser not installed")
            return []
        except subprocess.TimeoutExpired:
            print(f"    [skip] bb-browser twitter search timeout")
            continue
        except Exception as e:
            print(f"    [skip] bb-browser twitter: {str(e)[:40]}")
            continue
    if not results:
        print("    [skip] All Twitter sources failed")
    return results




# ── 新增数据源（第二梯队）─────────────
def fetch_youtube():
    """YouTube AI 相关视频搜索"""
    print("  Fetching YouTube...")
    results = []
    queries = [
        "AI agent workflow tutorial",
        "Claude Code Codex real project",
        "AI office automation beginner tutorial",
        "Doubao Qwen Kimi tutorial",
    ]
    for query in queries:
        try:
            r = subprocess.run(
                ["bb-browser", "site", "youtube/search", query, "--json"],
                capture_output=True, text=True, timeout=20
            )
            if r.returncode == 0 and r.stdout.strip():
                data = _safe_parse_browser_json(r.stdout)
                if not data:
                    continue
                videos = data.get("result", {}).get("videos", [])
                seen = set()
                for v in videos[:5]:
                    vid = v.get("url", v.get("videoId", ""))
                    if vid in seen:
                        continue
                    seen.add(vid)
                    results.append({
                        "title": v.get("title", ""),
                        "url": v.get("url", ""),
                        "channel": v.get("channel", ""),
                        "views": v.get("views", ""),
                        "published": v.get("publishedTime", "近期"),
                    })
        except FileNotFoundError:
            print("    [skip] bb-browser not installed")
            return []
        except subprocess.TimeoutExpired:
            continue
        except Exception as e:
            print(f"    [skip] youtube: {str(e)[:40]}")
            continue
    return results[:15]


def fetch_bilibili():
    """B站 AI 热门视频（通过 bb-browser）"""
    print("  Fetching Bilibili...")
    results = []
    queries = ["AI 办公 小白教程", "Agent Skill MCP 实战", "AI 编程 真实项目", "豆包 千问 Kimi 教程"]
    for query in queries:
        try:
            r = subprocess.run(
                ["bb-browser", "site", "bilibili/search", query, "10", "--json"],
                capture_output=True, text=True, timeout=20
            )
            if r.returncode == 0 and r.stdout.strip():
                data = _safe_parse_browser_json(r.stdout)
                if not data:
                    continue
                videos = data.get("result", {}).get("videos", [])
                seen = set()
                for v in (videos if isinstance(videos, list) else [videos]):
                    if not v.get("title") or _is_bilibili_scam(v.get("title", "")):
                        continue
                    vid = v.get("url", v.get("bvid", ""))
                    if vid in seen:
                        continue
                    seen.add(vid)
                    results.append({
                        "title": v.get("title", ""),
                        "url": v.get("url", ""),
                        "author": v.get("author", ""),
                        "views": v.get("view", ""),
                        "likes": v.get("like", ""),
                    })
        except FileNotFoundError:
            print("    [skip] bb-browser not installed")
            return []
        except subprocess.TimeoutExpired:
            continue
        except Exception as e:
            print(f"    [skip] bilibili: {str(e)[:40]}")
            continue
    return results[:15]


def fetch_zhihu():
    """知乎 AI 相关搜索（需要 bb-browser 已登录知乎）"""
    print("  Fetching Zhihu...")
    try:
        r = subprocess.run(
            ["bb-browser", "site", "zhihu/search", "AI 办公 Agent 工作流 小白教程", "10", "--json"],
            capture_output=True, text=True, timeout=20
        )
        if r.returncode == 0 and r.stdout.strip():
            data = _safe_parse_browser_json(r.stdout)
            if not data:
                return []
            items = data.get("result", {}).get("items", [])
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "replies": item.get("answer_count", item.get("comment_count", 0)),
                }
                for item in (items if isinstance(items, list) else [items])[:10]
                if item.get("title")
            ]
    except FileNotFoundError:
        print("    [skip] bb-browser not installed")
        return []
    except Exception as e:
        # 401 if not logged in — silent skip
        if "401" in str(e):
            print("    [skip] zhihu: not logged in (401)")
            return []
        print(f"    [skip] zhihu: {str(e)[:40]}")
        return []
    return []


def fetch_xiaohongshu():
    """小红书 AI 相关笔记（需要 bb-browser 已登录小红书）"""
    print("  Fetching Xiaohongshu...")
    try:
        r = subprocess.run(
            ["bb-browser", "site", "xiaohongshu/search", "AI 办公 教程 智能体", "--json"],
            capture_output=True, text=True, timeout=20
        )
        if r.returncode == 0 and r.stdout.strip():
            data = _safe_parse_browser_json(r.stdout)
            if not data:
                return []
            notes = data.get("result", {}).get("notes", [])
            return [
                {
                    "title": n.get("title", n.get("display_title", "")),
                    "url": n.get("url", ""),
                    "author": n.get("author", n.get("user", {}).get("nickname", "")),
                    "likes": n.get("likes", n.get("liked_count", 0)),
                    "comments": n.get("comments", n.get("comment_count", 0)),
                }
                for n in (notes if isinstance(notes, list) else [notes])[:10]
                if n.get("title") or n.get("display_title")
            ]
    except FileNotFoundError:
        print("    [skip] bb-browser not installed")
        return []
    except Exception as e:
        if "401" in str(e) or "Not logged in" in str(e):
            print("    [skip] xiaohongshu: not logged in")
            return []
        print(f"    [skip] xiaohongshu: {str(e)[:40]}")
        return []
    return []


def fetch_linuxdo():
    """Linux.do latest topics through the optional bb-browser adapter."""
    print("  Fetching Linux.do browser fallback...")
    try:
        result = subprocess.run(
            ["bb-browser", "site", "linuxdo/latest", "--json"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        payload = _safe_parse_browser_json(result.stdout) or {}
        topics = payload.get("result", {}).get("topics", [])
        if not isinstance(topics, list):
            topics = [topics]
        return [
            {
                "title": topic.get("title", ""),
                "url": topic.get("url")
                or (
                    f"https://linux.do/t/topic/{topic.get('id')}"
                    if topic.get("id")
                    else ""
                ),
                "description": topic.get("excerpt", "")
                or topic.get("description", ""),
                "replies": topic.get("reply_count", topic.get("posts_count", 0)),
            }
            for topic in topics[:10]
            if topic.get("title")
        ]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    except Exception as error:
        print(f"    [skip] Linux.do browser fallback: {str(error)[:80]}")
        return []


def fetch_googletrends():
    """Google Trends AI 关键词 7 日趋势（量化信号）"""
    print("  Fetching Google Trends...")
    if TrendReq is None:
        print("    [skip] pytrends not installed (pip install pytrends)")
        return []

    keywords = ["AI Agent", "Claude Code", "MCP", "豆包", "AI 办公"]
    try:
        pytrends = TrendReq(hl="zh-CN")
        pytrends.build_payload(keywords, timeframe="now 7-d")
        df = pytrends.interest_over_time()
        if df is None or df.empty:
            print("    [skip] Google Trends returned no data")
            return []

        df = df.drop(columns=["isPartial"], errors="ignore")

        # Calculate daily averages for a trend summary
        daily = df.resample("D").mean()
        results = []

        for kw in keywords:
            if kw not in daily.columns:
                continue
            series = daily[kw]
            avg = int(series.mean())
            first = series.iloc[0] if len(series) > 0 else 0
            last = series.iloc[-1] if len(series) > 0 else 0
            change = last - first
            if abs(change) < 3:
                trend = "→ 平稳"
            elif change > 0:
                trend = f"↑ +{int(change)}"
            else:
                trend = f"↓ {int(change)}"
            results.append({
                "title": f"Google Trends: {kw}",
                "description": f"7日均值 {avg} | 趋势 {trend}",
                "url": f"https://trends.google.com/trends/explore?q={kw.replace(' ', '+')}",
            })
        return results
    except Exception as e:
        err = str(e)
        if "429" in err or "Too Many" in err:
            print("    [skip] Google Trends rate limited (429)")
        else:
            print(f"    [skip] Google Trends: {err[:40]}")
        return []


def fetch_creator_opportunities(*, target_date=None):
    """Load still-open, curated creator programs from the checked-in radar."""
    path = BLOG_DIR / "src" / "data" / "ai-opportunities.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"    [skip] Creator opportunities: {error}")
        return []

    reference = target_date or datetime.now(CST).date()
    items = []
    for opportunity in payload.get("opportunities", []):
        deadline = opportunity.get("deadline")
        if deadline:
            try:
                if datetime.strptime(deadline, "%Y-%m-%d").date() < reference:
                    continue
            except ValueError:
                continue
        title = str(opportunity.get("title") or "").strip()
        url = str(opportunity.get("url") or "").strip()
        if not title or not url:
            continue
        timing = f"截止 {deadline}" if deadline else "长期开放"
        summary_parts = [
            str(opportunity.get("type") or "创作者计划"),
            timing,
            str(opportunity.get("reward") or "").strip(),
            str(opportunity.get("fit") or "").strip(),
        ]
        if opportunity.get("verification") != "official":
            continue
        items.append({
            "title": f"{opportunity.get('organizer', '')}：{title}".strip("："),
            "description": "；".join(part for part in summary_parts if part),
            "url": url,
        })
    return items


def build_source_registry():
    """Build the complete source set with portable primary/fallback ordering."""
    return SourceRegistry([
        CallableSource(
            "Hacker News",
            SourceTier.AGGREGATOR,
            lambda context: fetch_hackernews(
                n=context.limit,
                target_date=context.target_date if context.historical else None,
            ),
        ),
        CallableSource(
            "GitHub Trending",
            SourceTier.AGGREGATOR,
            lambda context: fetch_github_trending(
                target_date=context.target_date if context.historical else None,
            ),
        ),
        CallableSource(
            "V2EX",
            SourceTier.COMMUNITY,
            lambda _context: fetch_v2ex(),
            supports_historical=False,
        ),
        CallableSource(
            "HuggingFace Papers",
            SourceTier.AGGREGATOR,
            lambda context: fetch_huggingface(
                target_date=context.target_date if context.historical else None,
            ),
        ),
        CallableSource(
            "Product Hunt",
            SourceTier.AGGREGATOR,
            lambda _context: fetch_producthunt(),
            supports_historical=False,
        ),
        OpenAINewsSource(),
        AnthropicNewsSource(),
        OfficialRssSource(
            "GitHub Changelog",
            "https://github.blog/changelog/feed/",
            keywords=("copilot", "agent", "model", "MCP", "coding"),
        ),
        OfficialRssSource(
            "Cloudflare Blog",
            "https://blog.cloudflare.com/rss/",
            keywords=("AI", "Workers", "Agents", "developer", "model"),
        ),
        OfficialRssSource(
            "LangChain Blog",
            "https://blog.langchain.com/rss/",
            keywords=("agent", "LangGraph", "eval", "context", "memory"),
        ),
        LinuxDoSource(fallback=fetch_linuxdo),
        RedditSource(fallback=fetch_reddit),
        XSource(
            query=(
                "\"Agent Skills\" OR MCP OR RAG OR \"Claude Code\" OR Codex "
                "OR \"AI办公\" OR 豆包 OR Qwen OR Kimi OR \"AI创作者\""
            ),
            fallback=fetch_x_twitter,
        ),
        CallableSource(
            "YouTube",
            SourceTier.COMMUNITY,
            lambda _context: fetch_youtube(),
            supports_historical=False,
        ),
        CallableSource(
            "Bilibili",
            SourceTier.COMMUNITY,
            lambda _context: fetch_bilibili(),
            supports_historical=False,
        ),
        CallableSource(
            "Zhihu",
            SourceTier.COMMUNITY,
            lambda _context: fetch_zhihu(),
            supports_historical=False,
        ),
        XiaohongshuSource(fallback=fetch_xiaohongshu),
        CallableSource(
            "Google Trends",
            SourceTier.AGGREGATOR,
            lambda _context: fetch_googletrends(),
            supports_historical=False,
        ),
        CallableSource(
            "AI Creator Opportunities",
            SourceTier.OFFICIAL,
            lambda context: fetch_creator_opportunities(
                target_date=context.target_date,
            ),
            supports_historical=False,
        ),
    ])


def source_results_to_legacy(results):
    """Convert normalized evidence to the existing LLM/fallback input shape."""
    converted = {}
    for source, result in results.items():
        items = []
        for item in result.items:
            legacy = {
                "title": item.title,
                "url": item.url,
                "description": item.summary,
                "published_at": item.published_at,
                "author": item.author,
                "source_tier": item.source_tier.value,
            }
            legacy.update({
                key: value
                for key, value in item.engagement.items()
                if value is not None
            })
            items.append(legacy)
        converted[source] = items
    return converted


def filter_source_results(results, target_date, *, require_exact_date=False):
    """Remove unusable evidence before it reaches prompts or core quorum checks."""
    for result in results.values():
        before = len(result.items)
        result.items = filter_usable_items(
            result.items,
            target_date,
            require_exact_date=require_exact_date,
        )
        if before and not result.items:
            result.status = SourceStatus.SKIPPED
            reason = "all items failed URL/date quality checks"
            result.error = f"{result.error}; {reason}" if result.error else reason
    return results


# ── LLM 分析 ──────────────────────────
ANALYSIS_SYSTEM_PROMPT = """你是“AI 行动情报站”的主编。你服务的读者正在积累三类长期资产：Agent 工程与可靠工作流、面向普通人的 AI 办公教学、能交付和商业化的 AI 产品。你的任务不是覆盖整个行业，而是从原始数据中挑出能帮助读者学习、动手、产出作品或发现真实需求的信号。

今日数据来自以下来源：
- 官方类：OpenAI、Anthropic、GitHub Changelog、Cloudflare Blog、LangChain Blog
- 项目类：GitHub Trending、HackerNews、Product Hunt、HuggingFace Papers
- 社区类：Reddit、V2EX、Linux.do、X/Twitter、Zhihu、Xiaohongshu
- 视频类：YouTube、Bilibili
- 趋势类：Google Trends（7 日搜索量数据）
- 行动类：AI Creator Opportunities（仍可报名的官方创作者计划、征文和共建招募）
优先使用最近 48 小时的官方来源；社区内容只作为需求、情绪和案例线索。多个来源指向同一变化时合并报道，不以热度代替价值。

输出必须严格遵循以下格式（板块按顺序出现）：

## 01 今天真正重要的变化
只选 2-3 条会改变普通人使用 AI、团队交付 AI 或创作者生产内容方式的变化。每条写清：发生了什么、为什么重要、今天可以采取的一个小动作。

## 02 Agent 工程与工作流
优先 Skills、MCP、RAG、上下文、记忆、评测、可观测性和自动化。只选能提升可靠性、复用性或交付质量的内容，输出 2-4 条。

## 03 企业 AI 与办公落地
关注文档、表格、知识库、客服、培训、招投标和日常协作场景。把产品发布翻译成“小白或基层员工能完成什么工作”，输出 2-4 条。

## 04 AI 编程与开源实践
优先 Agent 工具链、TypeScript/React/Cloudflare 生态和可用于真实项目的开源项目。每条写：它是什么、适合谁、第一步怎么试。输出 3-5 条，不复述完整榜单。

## 05 产品、职业与内容机会
关注真实客户需求、可验证的产品方向、讲师与内容创作机会。只有官方活动数据可以作为可报名计划；社区收益截图只能表述为需求线索，不能写成已证实收益。输出 2-4 条。

## 06 值得持续关注
只有当证据足够但影响尚未完全展开时才输出，写清后续观察指标；否则跳过整个板块。

---

格式要求：
- 全部用中文
- 板块标题带编号前缀（01 02 03...）
- 每条目控制在 90-180 字，优先解释对读者的影响与下一步
- 每个观点必须附带来源 URL
- 只能使用原始数据中提供的 URL，不得补写、猜测或改造 URL
- 同一事件只能出现在一个板块；同一来源 URL 不得出现在多个编号条目，头条已使用的事件不在其他板块重复
- 社区来源必须明确写成“据社区讨论”或“有用户/开发者指出”
- 不得使用证据不支持的“最快”“第一”“唯一”“明确蓝海”等绝对表述
- 不在公开正文中出现“待核验”“规则待复核”“内部审核”等工作流标签；证据不足就删除，不把核验工作交给读者
- 如果某个板块今天没有值得输出的内容，跳过整个板块（标题也不保留）
"""


def generate_rss_feed(generated_at=None):
    """从所有 AI 日报 markdown 文件生成 RSS feed XML"""
    if not CONTENT_DIR.exists():
        return
    site_url = "https://blog.icemouce.cc"
    files = sorted(CONTENT_DIR.glob("????-??-??.md"), reverse=True)[:30]

    items = []
    for fp in files:
        text = fp.read_text(encoding="utf-8")
        title = ""
        pub_date = ""
        for line in text.split("\n")[:10]:
            if line.startswith("title: "):
                title = line.replace("title: ", "").strip().strip('"')
            elif line.startswith("date: "):
                date_str = line.replace("date: ", "").strip()
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0800")
                except ValueError:
                    pub_date = date_str
        if not title:
            title = "AI Daily Report"
        link = "%s/ai-daily/%s" % (site_url, fp.stem)
        body = text.split("---\n", 2)[-1] if "---\n" in text else text
        body_preview = "\n".join(
            line.rstrip()
            for line in re.sub(r"<[^>]+>", "", body[:500]).splitlines()
        ).strip()

        items.append(
            '    <item>'
            + '\n        <title><![CDATA[%s]]></title>' % title
            + '\n        <link>%s</link>' % link
            + '\n        <description><![CDATA[%s]]></description>' % body_preview.replace("]]>", "]]]]><![CDATA[")
            + '\n        <pubDate>%s</pubDate>' % pub_date
            + '\n        <guid>%s</guid>' % link
            + '\n    </item>'
        )

    items_xml = "\n".join(items)
    latest_issue = datetime.strptime(files[0].stem, "%Y-%m-%d").replace(
        tzinfo=CST
    )
    now_str = latest_issue.strftime("%a, %d %b %Y %H:%M:%S +0800")
    rss_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    rss_xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    rss_xml += '<channel>\n'
    rss_xml += '    <title>AI Daily - %s</title>\n' % site_url
    rss_xml += '    <link>%s</link>\n' % site_url
    rss_xml += '    <description>Daily AI industry news and trends, automatically generated</description>\n'
    rss_xml += '    <language>zh-CN</language>\n'
    rss_xml += '    <atom:link href="%s/ai-daily.xml" rel="self" type="application/rss+xml"/>\n' % site_url
    rss_xml += '    <lastBuildDate>%s</lastBuildDate>\n' % now_str
    rss_xml += items_xml + '\n'
    rss_xml += '</channel>\n'
    rss_xml += '</rss>\n'

    rss_path = BLOG_DIR / "public" / "ai-daily.xml"
    rss_path.parent.mkdir(parents=True, exist_ok=True)
    rss_path.write_text(rss_xml, encoding="utf-8")
    print("  [ok] RSS feed updated: %d items" % len(items))




def call_llm(raw_data_text):
    if not LLM_API_KEY:
        print("  [fail] No LLM API key found (set DEEPSEEK_API_KEY or OPENAI_API_KEY)")
        return None

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": "Raw data for today:\n\n" + raw_data_text},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [fail] LLM call failed: {e}")
        return None


def call_quality_repair(prompt):
    """Perform one deterministic repair pass for evidence-policy violations."""
    if not LLM_API_KEY:
        return None
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 AI 日报事实校对器。严格保留来源边界，"
                    "只输出修复后的 Markdown。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }).encode("utf-8")
    request = Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read())
            return result["choices"][0]["message"]["content"]
    except Exception as error:
        print(f"  [warn] Quality repair failed: {error}")
        return None


def call_trend_llm(prompt):
    """Request strict JSON for guarded cross-issue trend refreshes."""
    if not LLM_API_KEY:
        return None

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的 AI 行业研究编辑，只能输出符合用户约束的 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2400,
    }).encode("utf-8")
    req = Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
    )
    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as error:
        print(f"  [warn] Trend LLM call failed: {error}")
        return None


def format_raw_data(sources_data):
    lines = []
    for source_name, items in sources_data.items():
        if not items:
            continue
        lines.append(f"\n=== {source_name} ===")
        for i, item in enumerate(items[:8], 1):
            title = item.get("title", item.get("name", ""))
            url = item.get("url", "")
            desc = item.get("description", "")
            extras = []
            for key in ("score", "stars", "replies", "upvotes", "views", "likes", "comments"):
                if key in item and item[key]:
                    extras.append(f"{key}={item[key]}")
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            lines.append(f"  {i}. {title}{extra_str}\n     {url}\n     {desc[:200]}")
    return "\n".join(lines)


# ── 输出 ──────────────────────────────
def generate_markdown(report_content, date_str, generated_at=None):
    issue_date = datetime.strptime(date_str, "%Y-%m-%d")
    generated = generated_at or datetime.now(CST)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=CST)
    generated = generated.astimezone(CST)
    date_display = issue_date.strftime("%Y年%m月%d日")

    frontmatter = f"""---
title: "AI 行动情报站 - {date_display}"
date: {date_str}
description: 面向 Agent 工程、AI 办公教学与产品实践的每日行动情报
---

# AI 行动情报站 - {date_display}

> 只保留能帮助你理解变化、开始实践或积累作品的 AI 信号。信息来自产品官方、开源社区、开发者讨论与官方活动页。
> 编辑重点：Agent 工程与工作流、普通人的 AI 办公、AI 编程与开源实践、产品及创作者机会。

---

"""
    footer = f"""

---

*本情报由自动化系统于 {generated.strftime('%Y-%m-%d %H:%M')} 自动生成*"""
    return frontmatter + report_content.strip() + footer


def save_report(md_content, date_str, force=False):
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = CONTENT_DIR / f"{date_str}.md"
    if filepath.exists() and not force:
        existing = filepath.read_text(encoding="utf-8")
        fallback_markers = (
            "## Raw Data Summary",
            "## \U0001f4ca",
            "## 01 \U0001f4e1 \u539f\u59cb\u4fe1\u53f7\u5f52\u6863",
            "## 01 \U0001f4e1 \u4eca\u65e5\u6765\u6e90\u901f\u89c8",
        )
        if any(marker in existing for marker in fallback_markers):
            filepath.write_text(md_content, encoding="utf-8")
            print(f"  [ok] Overwrote: {filepath.name} (was fallback/non-llm)")
            return filepath
        print(f"  [skip] {filepath.name} already exists")
        return None
    filepath.write_text(md_content, encoding="utf-8")
    print(f"  [ok] Saved: {filepath.name}")
    return filepath


def _generate_fallback(sources_data):
    """Return a parseable signal archive when LLM analysis is unavailable."""
    parts = ["## 01 \U0001f4e1 \u4eca\u65e5\u6765\u6e90\u901f\u89c8", ""]
    for source_name, items in sources_data.items():
        valid_items = [
            item for item in items[:8]
            if (item.get("title") or item.get("name") or "").strip()
        ]
        if not valid_items:
            continue
        parts.append(f"### {source_name}")
        for item in valid_items:
            title = (item.get("title") or item.get("name") or "").strip()
            url = item.get("url", "")
            desc = (item.get("description") or "").strip()
            line = f"- **{title}**"
            if desc:
                line += f"\uff1a{desc[:120]}"
            if url:
                line += f" [\u94fe\u63a5]({url})"
            parts.append(line)
        parts.append("")
    if len(parts) == 2:
        parts.extend(["### \u7cfb\u7edf\u72b6\u6001", "- \u4eca\u65e5\u65e0\u6709\u6548\u6570\u636e\u3002"])
    return "\n".join(parts).strip()


# ── 主流程 ────────────────────────────
CORE_SOURCES = {
    "Hacker News",
    "GitHub Trending",
    "V2EX",
    "HuggingFace Papers",
    "Product Hunt",
    "OpenAI",
    "Anthropic",
}


def _existing_report_is_final(date_str):
    path = CONTENT_DIR / f"{date_str}.md"
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    fallback_markers = (
        "## Raw Data Summary",
        "## 📊",
        "## 01 📡 原始信号归档",
        "## 01 📡 今日来源速览",
    )
    return not any(marker in content for marker in fallback_markers)


def _refresh_derived_artifacts():
    generate_rss_feed()
    try:
        try:
            from scripts.ai_trends import refresh_trends
        except ModuleNotFoundError:
            from ai_trends import refresh_trends

        refreshed = refresh_trends(
            CONTENT_DIR,
            BLOG_DIR / "src" / "data" / "ai-trends.json",
            call_trend_llm,
        )
        if refreshed:
            print("  [ok] AI application trends refreshed")
    except Exception as error:
        print(f"  [warn] Trend refresh skipped: {error}")


def _run_generation(args):
    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    historical = target_date < datetime.now(CST).date()

    print("\n" + "=" * 50)
    print("  AI Daily Report Generator")
    print("=" * 50)
    print(f"\n  Date: {date_str} (CST)")
    print(f"  LLM: {LLM_MODEL} @ {LLM_BASE_URL.split('//')[1]}")
    if historical:
        print("  Mode: historical archive with exact-date evidence only")

    if (
        not args.dry_run
        and not args.force
        and _existing_report_is_final(date_str)
    ):
        print("  [info] Report already exists; refreshing derived artifacts")
        _refresh_derived_artifacts()
        return 0

    print("\n[1/3] Fetching registered data sources...")
    registry = build_source_registry()
    results = registry.fetch_all(
        SourceContext(
            target_date=target_date,
            limit=12,
            historical=historical,
        )
    )
    results = filter_source_results(
        results,
        target_date,
        require_exact_date=historical,
    )
    for source, result in results.items():
        detail = f"{len(result.items)} items"
        if result.error:
            detail += f" | {result.error[:100]}"
        print(f"  [{result.status.value}] {source}: {detail}")

    if not any(results[name].items for name in CORE_SOURCES):
        print("\n  [fail] All core sources returned no usable data.")
        return 1

    sources = source_results_to_legacy(results)
    active = {name: items for name, items in sources.items() if items}
    print(f"\n  Active sources: {len(active)}/{len(sources)}")

    print("\n[2/3] LLM analysis and automatic quality control...")
    raw_text = format_raw_data(active)
    report = call_llm(raw_text)
    if report:
        print(f"  [ok] Analysis done ({len(report)} chars)")
    else:
        print("  [warn] LLM unavailable; using evidence-only fallback")
        report = ""
    quality = validate_repair_or_fallback(
        report,
        results,
        target_date=target_date,
        repair=call_quality_repair if report else None,
        require_exact_date=historical,
    )
    print(f"  [ok] Quality mode: {quality.mode.value}")
    if quality.issues:
        print(f"  [info] Quality issues handled: {len(quality.issues)}")
        for issue in quality.issues:
            print(f"    - {issue}")

    if args.dry_run:
        print("\n[3/3] Dry run complete; no files were written.")
        print(quality.content)
        return 0

    print("\n[3/3] Writing validated artifacts...")
    markdown = generate_markdown(quality.content, date_str)
    filepath = save_report(markdown, date_str, force=args.force)
    if filepath is None and not _existing_report_is_final(date_str):
        print("  [fail] Existing report could not be replaced")
        return 1
    _refresh_derived_artifacts()
    return 0


def main(argv=None, *, publisher_factory=Publisher, generation_runner=None):
    args = parse_args(argv)
    runner = generation_runner or _run_generation
    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")

    if args.generate_only or args.dry_run:
        return runner(args)

    print("\n[AI Daily SOP] Publishing from an isolated origin/main worktree...")
    result = publisher_factory(BLOG_DIR).publish(date_str, force=args.force)
    print(
        f"  [ok] {result.status}: {result.commit_sha} "
        "(remote SHA and live RSS verified)"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped by user")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
