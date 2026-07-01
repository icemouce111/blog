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

# ── 数据源抓取 ────────────────────────
def fetch_hackernews(n=12):
    """Hacker News Top Stories (Firebase API)"""
    print("  Fetching Hacker News...")
    ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids:
        return []
    stories = []
    for sid in ids[:n]:
        item = _fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if item and item.get("title"):
            stories.append({
                "title": item["title"],
                "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                "score": item.get("score", 0),
                "by": item.get("by", ""),
            })
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

def fetch_github_trending():
    """GitHub Trending: HTML trending page first, API fallback with spam filter"""
    print("  Fetching GitHub Trending...")
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


def fetch_huggingface():
    """HuggingFace Daily Papers"""
    print("  Fetching HuggingFace Papers...")
    data = _fetch_json("https://huggingface.co/api/daily_papers")
    if not data:
        return []
    results = []
    for p in data[:10]:
        # Paper ID is nested under "paper" key in HF API response
        paper_obj = p.get("paper") or {}
        paper_id = paper_obj.get("id") or p.get("id", "")
        if not paper_id:
            paper_url = paper_obj.get("url") or p.get("paperUrl", "") or p.get("url", "")
            if paper_url:
                paper_id = paper_url.rstrip("/").rsplit("/", 1)[-1] if "/" in paper_url else ""
        url = f"https://huggingface.co/papers/{paper_id}" if paper_id else (paper_obj.get("url") or p.get("url", ""))
        results.append({
            "title": paper_obj.get("title") or p.get("title", ""),
            "url": url,
            "upvotes": p.get("upvotes", 0),
            "summary": (paper_obj.get("summary") or p.get("summary") or "")[:200],
        })
    return results


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
            items.append({
                "title": title_el.text if title_el is not None else "",
                "url": link_el.get("href") if link_el is not None else "",
                "description": summary,
            })
        return items[:10]
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
    queries = ["AI agents", "open source AI tools", "MCP protocol"]
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
    queries = ["AI agents 2026", "MCP protocol", "open source AI tools", "AI coding tools 2026"]
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
    queries = ["人工智能 大模型", "AI 开发 工具", "开源 AI 项目"]
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
            ["bb-browser", "site", "zhihu/search", "AI 人工智能 大模型 2026", "10", "--json"],
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
            ["bb-browser", "site", "xiaohongshu/search", "AI 人工智能", "--json"],
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

    keywords = ["AI agents", "Claude Code", "MCP protocol", "Cursor AI", "open source LLM"]
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


def build_source_registry():
    """Build the complete source set with portable primary/fallback ordering."""
    return SourceRegistry([
        CallableSource(
            "Hacker News",
            SourceTier.AGGREGATOR,
            fetch_hackernews,
        ),
        CallableSource(
            "GitHub Trending",
            SourceTier.AGGREGATOR,
            fetch_github_trending,
        ),
        CallableSource("V2EX", SourceTier.COMMUNITY, fetch_v2ex),
        CallableSource(
            "HuggingFace Papers",
            SourceTier.AGGREGATOR,
            fetch_huggingface,
        ),
        CallableSource(
            "Product Hunt",
            SourceTier.AGGREGATOR,
            fetch_producthunt,
        ),
        OpenAINewsSource(),
        AnthropicNewsSource(),
        LinuxDoSource(fallback=fetch_linuxdo),
        RedditSource(fallback=fetch_reddit),
        XSource(
            query="AI OR LLM OR \"Claude Code\" OR \"MCP protocol\"",
            fallback=fetch_x_twitter,
        ),
        CallableSource("YouTube", SourceTier.COMMUNITY, fetch_youtube),
        CallableSource("Bilibili", SourceTier.COMMUNITY, fetch_bilibili),
        CallableSource("Zhihu", SourceTier.COMMUNITY, fetch_zhihu),
        XiaohongshuSource(fallback=fetch_xiaohongshu),
        CallableSource(
            "Google Trends",
            SourceTier.AGGREGATOR,
            fetch_googletrends,
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


def filter_source_results(results, target_date):
    """Remove unusable evidence before it reaches prompts or core quorum checks."""
    for result in results.values():
        before = len(result.items)
        result.items = filter_usable_items(result.items, target_date)
        if before and not result.items:
            result.status = SourceStatus.SKIPPED
            reason = "all items failed URL/date quality checks"
            result.error = f"{result.error}; {reason}" if result.error else reason
    return results


# ── LLM 分析 ──────────────────────────
ANALYSIS_SYSTEM_PROMPT = """你是 AI 日报的编辑团队，采用 TradingAgents 多角色分析框架。基于今日原始数据，生成结构化的 AI 行业日报。

今日数据来自以下来源：
- 官方类：OpenAI News、Anthropic Newsroom
- 项目类：GitHub Trending、HackerNews、Product Hunt、HuggingFace Papers
- 社区类：Reddit、V2EX、Linux.do、X/Twitter、Zhihu、Xiaohongshu
- 视频类：YouTube、Bilibili
- 趋势类：Google Trends（7 日搜索量数据）
当多个来源指向同一信号时优先采用，并交叉验证。
优先使用最近 48 小时内的内容（检查发布时间字段）。

每个分析师角色各负责一个板块，板块顺序固定，内容独立产出。

输出必须严格遵循以下格式（板块按顺序出现）：

## 01 📌 今日头条
由主编汇总今日最重要的 3 条信号。每条标注**信号置信度**：高置信度（≥2源交叉验证）/ 中等置信度（单源+数据支撑）/ 单源信号。按置信度降序排列。

输出 3 条。

## 02 🔥 热门项目
**基础信号分析师** — 基于 GitHub Trending、HackerNews、Product Hunt、YouTube、Bilibili 等，识别今日最热门的项目和产品。每条用第一人称：我判断/我发现。
输出 4-6 条。

## 03 🗣️ 社区热议
**社区情绪分析师** — 基于 Reddit、V2EX、X/Twitter、Zhihu、Xiaohongshu 等社区讨论，捕捉今日开发者/用户在吵什么、焦虑什么、期待什么。每条包含：话题 + 情绪方向（兴奋/焦虑/质疑）+ 关键观点 + 来源链接。
输出 3-5 条。

## 04 💼 行业动态
**行业动态分析师** — 融资、收购、政策变化、市场格局调整。每条包含：事件 + 影响分析 + 来源链接。
输出 3-5 条。

## 05 🏗️ 技术趋势
**技术趋势分析师** — 架构变化、框架发布、重要模型的发布/更新、技术栈迁移信号。每条用第一人称：我发现/我推荐。
输出 3-5 条。

## 06 🎯 机会方向
**机会挖掘师** — 基于今日信号（含 Google Trends 的趋势数据），识别值得关注的方向：哪些关键词搜索量在涨、未被满足的需求、新兴场景、工具链空白。明确区分事实与编辑判断，不使用“蓝海”“必然”等无证据结论。
输出 3-5 条。

## 07 ⚠️ 风险提示
**风险提示师** — 争议事件、安全隐患、被淘汰的技术/工具、创始人/公司负面动态。
输出 2-4 条。

---

格式要求：
- 全部用中文
- 板块标题带编号前缀（01 02 03...）
- 今日头条以外的板块可用第一人称（我发现/我判断/我推荐）
- 今日头条每条标注 **[高置信度]** / **[中等置信度]** / **[单源信号]** 标签
- 每条目控制在 80-150 字，信息密度优先（去废话，留信号）
- 每个观点必须附带来源 URL
- 只能使用原始数据中提供的 URL，不得补写、猜测或改造 URL
- 社区来源必须明确写成“据社区讨论”或“有用户/开发者指出”
- 不得使用证据不支持的“最快”“第一”“唯一”“明确蓝海”等绝对表述
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
title: "AI 日报 - {date_display}"
date: {date_str}
description: 自动生成的每日 AI 行业动态汇总
---

# AI 日报 - {date_display}

> 每日 AI 行业动态自动汇总。信息来源于 Hacker News、GitHub、V2EX、HuggingFace、Product Hunt 等公开来源。
> 由 AI 分析师团队（基础信号/社区情绪/行业动态/技术趋势/机会挖掘/风险提示）多角色交叉分析生成。

---

"""
    footer = f"""

---

*本日报由自动化系统于 {generated.strftime('%Y-%m-%d %H:%M')} 自动生成*"""
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
    parts = ["## 01 \U0001f4e1 \u539f\u59cb\u4fe1\u53f7\u5f52\u6863", ""]
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

    print("\n" + "=" * 50)
    print("  AI Daily Report Generator")
    print("=" * 50)
    print(f"\n  Date: {date_str} (CST)")
    print(f"  LLM: {LLM_MODEL} @ {LLM_BASE_URL.split('//')[1]}")

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
        SourceContext(target_date=target_date, limit=12)
    )
    results = filter_source_results(results, target_date)
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
    result = publisher_factory(BLOG_DIR).publish(date_str)
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
