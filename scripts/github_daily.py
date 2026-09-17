#!/usr/bin/env python3
"""GitHub Daily generator — daily Star-growth board + AI digest, published branch-safely.

使用方式:
  python3 scripts/github_daily.py                # 抓取→解读→发布推送
  python3 scripts/github_daily.py --generate-only # 只生成 JSON 不发布
  python3 scripts/github_daily.py --dry-run       # 全流程不写文件

环境变量 (优先级从高到低):
  DESIRECORE_CLOUD_API_KEY + DESIRECORE_BASE_URL + DESIRECORE_MODEL
  DEEPSEEK_API_KEY
  OPENAI_API_KEY
缺少 key 时自动尝试加载 scripts/dc-config.env。无任何 key 时降级为
fallback 模式（榜单照发，AI 解读留空）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

try:
    from scripts.ai_daily_sop import PublishError, Publisher
    from scripts.github_trending import (
        TrendingFetchError,
        TrendingRepo,
        fetch_readme,
        fetch_trending,
        repo_to_payload,
    )
except ModuleNotFoundError:
    from ai_daily_sop import PublishError, Publisher
    from github_trending import (
        TrendingFetchError,
        TrendingRepo,
        fetch_readme,
        fetch_trending,
        repo_to_payload,
    )

CST = timezone(timedelta(hours=8))
SCRIPT_DIR = Path(__file__).resolve().parent
BLOG_DIR = SCRIPT_DIR.parent
DATA_DIR = BLOG_DIR / "src" / "data" / "github-daily"

TRENDING_LIMIT = 15
HIGHLIGHT_MIN = 3
HIGHLIGHT_MAX = 5
READER_PROFILE = (
    "正在系统积累 Agent 工程、可靠工作流和 AI 辅助全栈能力，"
    "同时要把真实实践转成面向小白的教程、可交付产品和个人品牌资产。"
)

SYSTEM_PROMPT = f"""你是开源项目解读编辑，服务一位特定读者：{READER_PROFILE}

输入是按今日新增 Star 排序的 GitHub Trending 榜单数据，**每个仓库附带了它的 README 内容**。你的任务：
1. 为榜单上的**每一个**仓库写三句话，**必须基于 README 的真实内容与架构来写，不得只复述或翻译官方简介**：
   - 「what」= 它是干啥的：说清核心功能、技术方案/架构要点（用什么实现的、有什么独到设计），全中文，不堆术语，出现英文专有名词时要顺带用中文解释它是什么
   - 「help」= 能解决什么问题、适合谁：基于 README 里描述的真实能力，不夸大
   - 「how」= 一个具体、可执行的开始方式：优先用 README 里写的安装/快速上手方式（如安装命令、CLI 用法），落到读者今天就能动手做的第一步
2. 从榜单中挑出 {HIGHLIGHT_MIN}~{HIGHLIGHT_MAX} 个最值得实践的项目作为「精选榜单」。优先级依次是：Agent/Skills/MCP/RAG/评测与工作流、TypeScript/React/Cloudflare 开发工具、企业 AI 与办公自动化、能转成小白教程的产品。每个写：title、why（为什么值得关注，结合 README 里的发展阶段/背景）、value、how（给出今天就能完成的第一步）。
3. 写一段 intro 今日榜单综述（80 字以内），概括今天榜单的整体风向。

严格只输出一个 JSON 对象，不要输出任何其他文字、解释或 markdown 代码块围栏，格式：
{{"intro": "...", "repos": [{{"repo": "owner/name", "what": "...", "help": "...", "how": "..."}}], "highlights": [{{"repo": "owner/name", "title": "...", "why": "...", "value": "...", "how": "..."}}]}}

硬性约束：
- repos 数组必须覆盖输入榜单的每一个仓库，各出现一次，顺序与榜单一致
- repo 字段必须与输入中的仓库全名完全一致（区分大小写）
- 每个 repos 条目的 what、help、how 都必须非空
- what 里禁止出现「官网介绍说」「简介称」这类转述腔——你就是读过 README 的编辑，直接陈述
- README 缺失或为「（未取到 README）」的仓库：基于官方简介与语言生态写保守解读，并用中文
- highlights 的 repo 必须来自输入榜单
- 所有文案使用简体中文"""


_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def _is_mostly_chinese(text: str, *, min_cjk: int = 4) -> bool:
    """Reject English-only output (e.g. echoed GitHub descriptions)."""
    return len(_CJK_PATTERN.findall(text)) >= min_cjk


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs into os.environ without overriding existing vars."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _llm_settings() -> tuple[str | None, str, str]:
    api_key = (
        os.environ.get("DESIRECORE_CLOUD_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if os.environ.get("DESIRECORE_CLOUD_API_KEY"):
        base_url = os.environ.get("DESIRECORE_BASE_URL", "").rstrip("/")
        model = os.environ.get("DESIRECORE_MODEL", "")
    elif os.environ.get("DEEPSEEK_API_KEY"):
        base_url, model = "https://api.deepseek.com/v1", "deepseek-chat"
    else:
        base_url, model = "https://api.openai.com/v1", "gpt-4o"
    return api_key, base_url, model


def fetch_readmes(
    repos: list[TrendingRepo], *, max_workers: int = 5
) -> dict[str, str]:
    """Fetch READMEs concurrently; failures degrade to '' per repo, never raise."""
    from concurrent.futures import ThreadPoolExecutor

    results: dict[str, str] = {}

    def worker(repo: TrendingRepo) -> tuple[str, str]:
        try:
            return repo.full_name, fetch_readme(repo.full_name)
        except Exception:
            return repo.full_name, ""

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for full_name, readme in pool.map(worker, repos):
            results[full_name] = readme
    return results


def build_user_prompt(repos: list[TrendingRepo], readmes: dict[str, str] | None = None) -> str:
    readmes = readmes or {}
    lines = ["今日 GitHub Trending 每日新增 Star 排行："]
    for repo in repos:
        stars = f"{repo.stars} total stars" if repo.stars is not None else "stars 未知"
        today = (
            f"，今日 +{repo.stars_today}"
            if repo.stars_today is not None
            else ""
        )
        topics = f" | topics: {', '.join(repo.topics)}" if repo.topics else ""
        lines.append(
            f"{repo.rank}. {repo.full_name} | 语言: {repo.language or '未知'}"
            f" | {stars}{today}{topics}\n"
            f"   官方简介: {repo.description or '（无）'}\n"
            f"   地址: {repo.url}"
        )
        readme = readmes.get(repo.full_name, "").strip()
        if readme:
            lines.append("   README 节选:")
            for readme_line in readme.splitlines():
                lines.append(f"     {readme_line}")
        else:
            lines.append("   README: （未取到 README，请基于官方简介保守解读）")
    lines.append(
        f"\n请输出 JSON：repos 覆盖以上全部 {len(repos)} 个仓库，且每项都有 what、help、how；"
        f"what/help/how 必须基于 README 内容用简体中文撰写；"
        f"highlights 挑 {HIGHLIGHT_MIN}~{HIGHLIGHT_MAX} 个；附 intro 综述。"
    )
    return "\n".join(lines)


def call_llm(
    prompt: str, api_key: str, base_url: str, model: str
) -> str | None:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 8192,
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read())
            return result["choices"][0]["message"]["content"]
    except Exception as error:
        print(f"  [warn] LLM call failed: {error}")
        return None


def extract_json(content: str) -> Any:
    text = content.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def validate_payload(payload: Any, repos: list[TrendingRepo]) -> dict[str, Any]:
    """Strictly validate the LLM JSON; raise ValueError with a precise reason."""
    if not isinstance(payload, dict):
        raise ValueError("payload is not a JSON object")
    names = {repo.full_name.lower(): repo.full_name for repo in repos}

    intro = str(payload.get("intro") or "").strip()
    if not intro:
        raise ValueError("intro is empty")

    raw_projects = payload.get("repos")
    if not isinstance(raw_projects, list) or not raw_projects:
        raise ValueError("repos missing or empty")
    projects: dict[str, dict[str, str]] = {}
    for entry in raw_projects:
        if not isinstance(entry, dict):
            raise ValueError("repo entry is not an object")
        repo = str(entry.get("repo") or "").strip()
        canonical = names.get(repo.lower())
        if canonical is None:
            raise ValueError(f"unknown repo: {repo}")
        if canonical in projects:
            raise ValueError(f"duplicate repo: {repo}")
        what = str(entry.get("what") or "").strip()
        help_text = str(entry.get("help") or "").strip()
        how = str(entry.get("how") or "").strip()
        if not what or not help_text or not how:
            raise ValueError(f"what/help/how missing for {repo}")
        if not _is_mostly_chinese(what):
            raise ValueError(f"what is not Chinese for {repo}: {what[:60]}")
        if not _is_mostly_chinese(help_text):
            raise ValueError(f"help is not Chinese for {repo}")
        projects[canonical] = {"what": what, "help": help_text, "how": how}
    missing = sorted(set(names.values()) - set(projects))
    if missing:
        raise ValueError(f"repos not fully covered, missing: {', '.join(missing)}")

    raw_highlights = payload.get("highlights")
    if not isinstance(raw_highlights, list) or not (
        HIGHLIGHT_MIN <= len(raw_highlights) <= HIGHLIGHT_MAX
    ):
        raise ValueError(
            f"highlights must contain {HIGHLIGHT_MIN}-{HIGHLIGHT_MAX} entries"
        )
    highlights: list[dict[str, str]] = []
    for entry in raw_highlights:
        if not isinstance(entry, dict):
            raise ValueError("highlight entry is not an object")
        repo = str(entry.get("repo") or "").strip()
        canonical = names.get(repo.lower())
        if canonical is None:
            raise ValueError(f"highlight references unknown repo: {repo}")
        fields = {
            key: str(entry.get(key) or "").strip()
            for key in ("title", "why", "value", "how")
        }
        incomplete = [key for key, value in fields.items() if not value]
        if incomplete:
            raise ValueError(
                f"highlight fields {incomplete} incomplete for {repo}"
            )
        highlights.append({"repo": canonical, **fields})
    return {"intro": intro, "projects": projects, "highlights": highlights}


def build_record(
    date_str: str,
    repos: list[TrendingRepo],
    payload: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    analyzed = payload is not None
    record_repos: list[dict[str, Any]] = []
    for repo in repos:
        project = (payload or {}).get("projects", {}).get(repo.full_name, {})
        what = project.get("what", "")
        if not what:
            # fallback: never echo the raw (usually English) GitHub blurb;
            # leave what empty so the UI shows its own honest placeholder.
            what = ""
        record_repos.append(
            {
                **repo_to_payload(repo),
                "what": what,
                "help": project.get("help", ""),
                "how": project.get("how", ""),
            }
        )
    return {
        "date": date_str,
        "generatedAt": generated_at,
        "mode": "analyzed" if analyzed else "fallback",
        "intro": (
            payload["intro"]
            if analyzed
            else "今日 AI 解读暂缺，以下为 GitHub 原始榜单。"
        ),
        "repos": record_repos,
        "highlights": payload["highlights"] if analyzed else [],
    }


def save_record(
    record: dict[str, Any], date_str: str, *, force: bool
) -> Path | None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"{date_str}.json"
    if filepath.exists() and not force:
        try:
            existing = json.loads(filepath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict) and existing.get("mode") == "analyzed":
            print(f"  [skip] {filepath.name} already analyzed (use --force)")
            return None
        filepath.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  [ok] Overwrote: {filepath.name} (was fallback/invalid)")
        return filepath
    filepath.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  [ok] Saved: {filepath.name}")
    return filepath


def run_generation(args: argparse.Namespace) -> int:
    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    api_key, base_url, model = _llm_settings()

    print("\n" + "=" * 50)
    print("  GitHub Daily Generator")
    print("=" * 50)
    print(f"\n  Date: {date_str} (CST)")
    print(
        f"  LLM: {model or 'disabled'} @ "
        f"{base_url.split('//')[-1] if base_url else '-'}"
    )

    print(f"\n[1/3] Fetching GitHub Trending daily Star growth (top {TRENDING_LIMIT})...")
    try:
        repos = fetch_trending(limit=TRENDING_LIMIT)
    except TrendingFetchError as error:
        print(f"  [fail] {error}")
        return 1
    for repo in repos:
        today = f" +{repo.stars_today}" if repo.stars_today is not None else ""
        print(f"  {repo.rank:>2}. {repo.full_name} [{repo.language or '?'}]{today}")

    print(f"\n[2/4] Fetching READMEs (so the AI reads the project, not just the blurb)...")
    readmes = fetch_readmes(repos)
    got = sum(1 for value in readmes.values() if value)
    print(f"  [ok] READMEs: {got}/{len(repos)}")

    print("\n[3/4] AI digest...")
    payload = None
    if api_key and base_url and model:
        content = call_llm(build_user_prompt(repos, readmes), api_key, base_url, model)
        if content:
            try:
                payload = validate_payload(extract_json(content), repos)
                print(
                    f"  [ok] Digest done ({len(payload['projects'])} repos, "
                    f"{len(payload['highlights'])} highlights)"
                )
            except (ValueError, json.JSONDecodeError) as error:
                print(f"  [warn] LLM payload invalid: {error}")
        else:
            print("  [warn] LLM call failed")
    else:
        print("  [warn] No LLM credentials configured")
    if payload is None:
        print("  [warn] Falling back to raw board mode")

    if args.dry_run:
        print("\n[4/4] Dry run complete; no files were written.")
        preview = build_record(
            date_str, repos, payload, datetime.now(CST).strftime("%Y-%m-%d %H:%M")
        )
        print(json.dumps(preview, ensure_ascii=False, indent=2)[:3000])
        return 0

    print("\n[4/4] Writing record...")
    record = build_record(
        date_str, repos, payload, datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    )
    filepath = save_record(record, date_str, force=args.force)
    if filepath is None:
        print("  [info] Existing analyzed record kept; nothing written")
    return 0


def publisher_artifacts(date: str) -> set[str]:
    return {f"src/data/github-daily/{date}.json"}


def publisher_commit_message(date: str) -> str:
    return f"chore: add GitHub daily trending for {date}"


def publisher_remote_artifact(date: str) -> str:
    return f"src/data/github-daily/{date}.json"


def run_publisher(date_str: str, *, force: bool) -> int:
    def generate(worktree: Path, date: str) -> None:
        command = [
            sys.executable,
            str(worktree / "scripts" / "github_daily.py"),
            "--generate-only",
            "--date",
            date,
        ]
        if force:
            command.append("--force")
        result = subprocess.run(
            command,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=15 * 60,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise PublishError(f"GitHub Daily generation failed: {detail}")

    publisher = Publisher(
        BLOG_DIR,
        artifacts=publisher_artifacts,
        commit_message=publisher_commit_message,
        remote_artifact=publisher_remote_artifact,
        live_url=None,
    )
    result = publisher.publish(date_str, force=force, generate=generate)
    print(f"  [ok] {result.status}: {result.commit_sha} (remote SHA verified)")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and publish GitHub Daily"
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate the JSON record without Git publication",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and digest without writing files or publishing",
    )
    parser.add_argument(
        "--date",
        help="Target date in YYYY-MM-DD format (defaults to today in CST)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing record for the target date",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    if args.generate_only or args.dry_run:
        return run_generation(args)
    return run_publisher(date_str, force=args.force)


if __name__ == "__main__":
    load_env_file(SCRIPT_DIR / "dc-config.env")
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Stopped by user")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
