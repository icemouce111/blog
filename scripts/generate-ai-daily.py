#!/usr/bin/env python3
"""
AI 日报生成器 — 每日自动抓取与分析

使用方式:
  python3 scripts/generate-ai-daily.py

依赖: stdlib only (零外部依赖)

流程:
  1. 并行抓取 6 个免费数据源
  2. LLM 多角色分析师 (7 个角色) 分析
  3. 生成 markdown 日报文件
  4. 写入 src/content/ai-daily/
  5. git commit + push → Cloudflare 自动部署

环境变量:
  DEEPSEEK_API_KEY (推荐) or OPENAI_API_KEY — LLM 调用
  GITHUB_TOKEN or GH_TOKEN — git push 认证（可选，默认走 SSH）
"""

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


def fetch_github_trending():
    """GitHub Trending — GitHub Search API + HTML fallback"""
    print("  Fetching GitHub Trending...")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    yesterday = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = _fetch_json(
        f"https://api.github.com/search/repositories?q=created:>={yesterday}&sort=stars&order=desc&per_page=10",
        headers,
    )
    if data and "items" in data:
        return [
            {
                "name": r["full_name"],
                "description": r.get("description") or "",
                "stars": r.get("stargazers_count", 0),
                "url": r["html_url"],
                "language": r.get("language") or "",
            }
            for r in data["items"]
        ]
    # HTML fallback -- try optional BeautifulSoup first for more robust parsing
    html = _fetch("https://github.com/trending")
    if not html:
        return []
    text = html.decode("utf-8", errors="replace")
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
            owner, name = href.split("/", 1)

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

            repos.append({
                "name": f"{owner}/{name}",
                "description": desc[:200],
                "url": f"https://github.com/{owner}/{name}",
                "language": language,
                "stars": stars,
            })
    else:
        # Improved regex fallback
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
            repos.append({
                "name": f"{owner}/{name_part}",
                "description": desc[:200],
                "url": f"https://github.com/{owner}/{name_part}",
                "language": language,
                "stars": 0,
            })
    return repos[:10]


def fetch_v2ex():
    """V2EX 最热主题"""
    print("  Fetching V2EX...")
    data = _fetch_json("https://www.v2ex.com/api/topics/hot.json")
    if not data:
        return []
    return [
        {
            "title": t.get("title", ""),
            "url": f"https://www.v2ex.com/t/{t.get('id', '')}",
            "node": t.get("node", {}).get("title", ""),
            "replies": t.get("replies", 0),
        }
        for t in data[:15]
    ]


def fetch_huggingface():
    """HuggingFace Daily Papers"""
    print("  Fetching HuggingFace Papers...")
    data = _fetch_json("https://huggingface.co/api/daily_papers")
    if not data:
        return []
    return [
        {
            "title": p.get("title", ""),
            "url": f"https://huggingface.co/papers/{p.get('id', '')}",
            "upvotes": p.get("upvotes", 0),
            "summary": (p.get("summary") or "")[:200],
        }
        for p in data[:10]
    ]


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
                    if not v.get("title"):
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
    """知乎 AI 热门讨论（需要 bb-browser 已登录知乎）"""
    print("  Fetching Zhihu...")
    try:
        r = subprocess.run(
            ["bb-browser", "site", "zhihu/hot", "10", "--json"],
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


# ── LLM 分析 ──────────────────────────
ANALYSIS_SYSTEM_PROMPT = """你是 AI 日报的编辑团队，采用 TradingAgents 多角色分析框架。基于今日原始数据，生成结构化的 AI 行业日报。

今日数据来自以下来源：
- 项目类：GitHub Trending、HackerNews、Product Hunt、HuggingFace Papers
- 社区类：Reddit、V2EX、X/Twitter、Zhihu、Xiaohongshu
- 视频类：YouTube、Bilibili
- 趋势类：Google Trends（7 日搜索量数据）
当多个来源指向同一信号时优先采用，并交叉验证。
优先使用最近 48 小时内的内容（检查发布时间字段）。

每个分析师角色各负责一个板块，板块顺序固定，内容独立产出。

输出必须严格遵循以下格式（板块按顺序出现）：

## 📌 今日头条
由主编汇总今日最重要的 3 条信号。每条包含：发生了什么 + 为什么重要 + 来源链接。

## 🔥 今日热门项目
**基础信号分析师** — 基于 GitHub Trending、HackerNews、Product Hunt、YouTube、Bilibili 等，识别今日最热门的项目和产品。每个项目包含：项目名 + 核心功能简介 + 热度信号（stars/upvotes/views）+ 来源链接。
输出 4-6 条。

## 🗣️ 社区热议
**社区情绪分析师** — 基于 Reddit、V2EX、X/Twitter、Zhihu、Xiaohongshu 等社区讨论，捕捉今日开发者/用户在吵什么、焦虑什么、期待什么。每条包含：话题 + 情绪方向（兴奋/焦虑/质疑） + 关键观点 + 来源链接。
输出 3-5 条。

## 💼 行业动态
**行业动态分析师** — 融资、收购、政策变化、市场格局调整。每条包含：事件 + 影响分析 + 来源链接。
输出 3-5 条。

## 🏗️ 技术趋势
**技术趋势分析师** — 架构变化、框架发布、重要模型的发布/更新、技术栈迁移信号。每条包含：变化 + 技术要点 + 影响判断 + 来源链接。
输出 3-5 条。

## 🎯 机会方向
**机会挖掘师** — 基于今日信号（含 Google Trends 的趋势数据），识别值得关注的方向：哪些关键词搜索量在涨、未被满足的需求、新兴场景、工具链空白。每条包含：方向 + 做什么 + 为什么是现在 + 来源链接。
输出 3-5 条。

## ⚠️ 风险提示
**风险提示师** — 争议事件、安全隐患、被淘汰的技术/工具、创始人/公司负面动态。
输出 2-4 条。

---

格式要求：
- 全部用中文
- 以上 6 个分析师角色各负责一个对应板块，板块标题即角色标识（不额外输出角色名）
- 每个条目控制在 80-120 字以内
- 每个观点必须附带来源 URL
- 如果某个板块今天没有值得输出的内容，可以整个板块跳过（保留板块标题即可）
"""


def generate_rss_feed():
    """从所有 AI 日报 markdown 文件生成 RSS feed XML"""
    if not CONTENT_DIR.exists():
        return
    site_url = "https://blog.icemouce.com"
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
        body_preview = re.sub(r"<[^>]+>", "", body[:500]).strip()

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
    now_str = datetime.now(CST).strftime("%a, %d %b %Y %H:%M:%S +0800")
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
def generate_markdown(report_content, date_str):
    today = datetime.now(CST)
    date_display = today.strftime("%Y年%m月%d日")

    frontmatter = f"""---
title: "AI 日报 - {date_display}"
date: {today.strftime("%Y-%m-%d")}
description: 自动生成的每日 AI 行业动态汇总
---

# AI 日报 - {date_display}

> 每日 AI 行业动态自动汇总。信息来源于 Hacker News、GitHub、V2EX、HuggingFace、Product Hunt 等公开来源。
> 由 AI 分析师团队（基础信号/社区情绪/行业动态/技术趋势/机会挖掘/风险提示）多角色交叉分析生成。

---

"""
    footer = f"""

---

*本日报由自动化系统于 {today.strftime('%Y-%m-%d %H:%M')} 自动生成*"""
    return frontmatter + report_content.strip() + footer


def save_report(md_content, date_str, force=False):
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = CONTENT_DIR / f"{date_str}.md"
    if filepath.exists() and not force:
        existing = filepath.read_text(encoding="utf-8")
        if "## Raw Data Summary" in existing:
            filepath.write_text(md_content, encoding="utf-8")
            print(f"  [ok] Overwrote: {filepath.name} (was fallback)")
            return filepath
        print(f"  [skip] {filepath.name} already exists")
        return None
    filepath.write_text(md_content, encoding="utf-8")
    print(f"  [ok] Saved: {filepath.name}")
    return filepath


def git_commit_push(date_str):
    print("  Committing & pushing...")
    try:
        add = subprocess.run(
            ["git", "add", "src/content/ai-daily/"],
            capture_output=True, text=True, timeout=30, cwd=BLOG_DIR,
        )
        if add.returncode != 0:
            print(f"  [fail] git add: {add.stderr.strip()}")
            return False

        commit = subprocess.run(
            ["git", "commit", "-m", f"chore: add AI daily report for {date_str}"],
            capture_output=True, text=True, timeout=30, cwd=BLOG_DIR,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            print(f"  [fail] git commit: {commit.stderr.strip() or commit.stdout.strip()}")
            return False
        if "nothing to commit" in commit.stdout:
            print("  [ok] Nothing new to commit")
            return True

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            remote = f"https://x-access-token:{token}@github.com/icemouce111/blog.git"
            push = subprocess.run(
                ["git", "push", remote, "main"],
                capture_output=True, text=True, timeout=60, cwd=BLOG_DIR,
            )
        else:
            push = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True, text=True, timeout=60, cwd=BLOG_DIR,
            )

        if push.returncode == 0:
            print("  [ok] Pushed to GitHub, Cloudflare will auto-deploy")
            return True
        else:
            print(f"  [fail] git push: {push.stderr.strip()[:300]}")
            return False

    except subprocess.TimeoutExpired:
        print("  [fail] git push timeout")
        return False
    except Exception as e:
        print(f"  [fail] git error: {e}")
        return False


# ── 主流程 ────────────────────────────
def main():

    print("\n" + "=" * 50)
    print("  AI Daily Report Generator")
    print("=" * 50)

    today = datetime.now(CST)
    date_str = today.strftime("%Y-%m-%d")
    print(f"\n  Date: {today.strftime('%Y-%m-%d')} (CST)")
    print(f"  LLM: {LLM_MODEL} @ {LLM_BASE_URL.split('//')[1]}")

    # 1. Fetch
    print("\n[1/4] Fetching data sources...")
    sources: dict[str, list] = {
        "Hacker News": fetch_hackernews(),
    "GitHub Trending": fetch_github_trending(),
    "V2EX": fetch_v2ex(),
    "HuggingFace Papers": fetch_huggingface(),
    "Product Hunt": fetch_producthunt(),
    "Reddit": fetch_reddit(),
    "X/Twitter": fetch_x_twitter(),
    "YouTube": fetch_youtube(),
    "Bilibili": fetch_bilibili(),
    "Zhihu": fetch_zhihu(),
    "Xiaohongshu": fetch_xiaohongshu(),
    "Google Trends": fetch_googletrends(),
    }

    active = {k: v for k, v in sources.items() if v}
    print(f"\n  Active sources: {len(active)}/{len(sources)}")
    for k, v in active.items():
        print(f"    - {k}: {len(v)} items")
    if not active:
        print("\n  [fail] All sources failed. Check network.")
        return 1

    # 2. Analyze
    print("\n[2/4] LLM analysis...")
    raw_text = format_raw_data(active)
    print(f"  Raw data: ~{len(raw_text)} chars")
    report = call_llm(raw_text)
    if report:
        print(f"  [ok] Analysis done ({len(report)} chars)")
    else:
        print("  [warn] LLM failed, using raw data as fallback")
        report = "## Raw Data Summary\n\n" + raw_text

    # 3. Generate
    print("\n[3/4] Generating markdown...")
    md_content = generate_markdown(report, date_str)
    should_force = "--force" in sys.argv
    filepath = save_report(md_content, date_str, force=should_force)
    if not filepath:
        print("  [skip] Report already exists for today")
        return 0
    generate_rss_feed()

    # 4. Push
    print("\n[4/4] Deploying...")
    pushed = git_commit_push(date_str)

    print("\n" + "=" * 50)
    if pushed:
        print("  [ok] Done! Report generated and deployed.")
    else:
        print("  [warn] Report saved locally. Push may need manual action.")
    print("=" * 50 + "\n")
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
