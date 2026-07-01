import importlib.util
import pathlib
import tempfile
import unittest
from datetime import date, datetime, timezone

from scripts.ai_daily_sources import (
    SourceItem,
    SourceResult,
    SourceStatus,
    SourceTier,
)


MODULE_PATH = pathlib.Path(__file__).with_name("generate-ai-daily.py")
SPEC = importlib.util.spec_from_file_location("generate_ai_daily", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerateFallbackTest(unittest.TestCase):
    def test_fallback_uses_numbered_archive_and_source_subheadings(self):
        output = MODULE._generate_fallback({
            "Hacker News": [{
                "title": "A signal",
                "description": "A description",
                "url": "https://example.com/signal",
            }]
        })

        self.assertTrue(output.startswith("## 01 📡 原始信号归档"))
        self.assertIn("### Hacker News", output)
        self.assertNotIn("## 📊 Hacker News", output)
        self.assertIn("[链接](https://example.com/signal)", output)

    def test_empty_fallback_keeps_the_archive_contract(self):
        output = MODULE._generate_fallback({})

        self.assertTrue(output.startswith("## 01 📡 原始信号归档"))
        self.assertIn("### 系统状态", output)


class GenerateRssFeedTest(unittest.TestCase):
    def test_rss_uses_the_live_cc_domain(self):
        original_blog_dir = MODULE.BLOG_DIR
        original_content_dir = MODULE.CONTENT_DIR

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            content_dir = root / "src" / "content" / "ai-daily"
            content_dir.mkdir(parents=True)
            (root / "public").mkdir()
            (content_dir / "2026-06-29.md").write_text(
                """---
title: "AI 日报 - 2026年06月29日"
date: 2026-06-29
---

## 01 📌 今日头条

1. **今日信号**
""",
                encoding="utf-8",
            )

            try:
                MODULE.BLOG_DIR = root
                MODULE.CONTENT_DIR = content_dir
                MODULE.generate_rss_feed()
                rss = (root / "public" / "ai-daily.xml").read_text(encoding="utf-8")
            finally:
                MODULE.BLOG_DIR = original_blog_dir
                MODULE.CONTENT_DIR = original_content_dir

        self.assertIn("https://blog.icemouce.cc/ai-daily/2026-06-29", rss)
        self.assertNotIn("https://blog.icemouce.com", rss)

    def test_rss_is_idempotent_across_reruns(self):
        original_blog_dir = MODULE.BLOG_DIR
        original_content_dir = MODULE.CONTENT_DIR

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            content_dir = root / "src" / "content" / "ai-daily"
            content_dir.mkdir(parents=True)
            (root / "public").mkdir()
            (content_dir / "2026-07-01.md").write_text(
                """---
title: "AI 日报 - 2026年07月01日"
date: 2026-07-01
---

## 01 📌 今日头条
""",
                encoding="utf-8",
            )

            try:
                MODULE.BLOG_DIR = root
                MODULE.CONTENT_DIR = content_dir
                MODULE.generate_rss_feed(
                    generated_at=datetime(2026, 7, 1, 8, tzinfo=timezone.utc)
                )
                first = (root / "public" / "ai-daily.xml").read_text(
                    encoding="utf-8"
                )
                MODULE.generate_rss_feed(
                    generated_at=datetime(2026, 7, 2, 8, tzinfo=timezone.utc)
                )
                second = (root / "public" / "ai-daily.xml").read_text(
                    encoding="utf-8"
                )
            finally:
                MODULE.BLOG_DIR = original_blog_dir
                MODULE.CONTENT_DIR = original_content_dir

        self.assertEqual(first, second)


class CliContractTest(unittest.TestCase):
    def test_parses_generation_and_recovery_flags(self):
        args = MODULE.parse_args([
            "--generate-only",
            "--dry-run",
            "--force",
            "--date",
            "2026-07-01",
        ])

        self.assertTrue(args.generate_only)
        self.assertTrue(args.dry_run)
        self.assertTrue(args.force)
        self.assertEqual(args.date, "2026-07-01")

    def test_default_entrypoint_delegates_to_isolated_publisher(self):
        events = []

        class FakePublisher:
            def __init__(self, repo_root):
                events.append(("init", repo_root))

            def publish(self, date):
                events.append(("publish", date))
                return type(
                    "Result",
                    (),
                    {"status": "published", "commit_sha": "abc123"},
                )()

        code = MODULE.main(
            ["--date", "2026-07-01"],
            publisher_factory=FakePublisher,
            generation_runner=lambda _args: self.fail(
                "default mode must not generate in the shared checkout"
            ),
        )

        self.assertEqual(code, 0)
        self.assertEqual(events[-1], ("publish", "2026-07-01"))

    def test_generate_only_runs_generation_without_publisher(self):
        calls = []

        code = MODULE.main(
            ["--generate-only", "--date", "2026-07-01"],
            publisher_factory=lambda _root: self.fail(
                "generate-only must not publish"
            ),
            generation_runner=lambda args: calls.append(args) or 0,
        )

        self.assertEqual(code, 0)
        self.assertEqual(calls[0].date, "2026-07-01")


class SourceRegistryContractTest(unittest.TestCase):
    def test_registry_contains_legacy_and_new_sources(self):
        names = {
            adapter.name
            for adapter in MODULE.build_source_registry().adapters
        }

        self.assertEqual(
            names,
            {
                "Hacker News",
                "GitHub Trending",
                "V2EX",
                "HuggingFace Papers",
                "Product Hunt",
                "OpenAI",
                "Anthropic",
                "Linux.do",
                "Reddit",
                "X/Twitter",
                "YouTube",
                "Bilibili",
                "Zhihu",
                "Xiaohongshu",
                "Google Trends",
            },
        )

    def test_filters_registered_results_before_llm_analysis(self):
        results = {
            "OpenAI": SourceResult(
                "OpenAI",
                SourceStatus.ACTIVE,
                [
                    SourceItem(
                        source="OpenAI",
                        title="Current",
                        url="https://openai.com/current",
                        published_at="2026-06-30",
                        source_tier=SourceTier.OFFICIAL,
                    ),
                    SourceItem(
                        source="OpenAI",
                        title="Future",
                        url="https://openai.com/future",
                        published_at="2026-07-10",
                        source_tier=SourceTier.OFFICIAL,
                    ),
                ],
            )
        }

        filtered = MODULE.filter_source_results(results, date(2026, 7, 1))

        self.assertEqual(
            [item.title for item in filtered["OpenAI"].items],
            ["Current"],
        )


class MarkdownDateTest(unittest.TestCase):
    def test_historical_generation_uses_requested_date(self):
        generated = datetime(2026, 7, 2, 1, 30, tzinfo=timezone.utc)

        markdown = MODULE.generate_markdown(
            "## 01 📌 今日头条\n",
            "2026-07-01",
            generated_at=generated,
        )

        self.assertIn('title: "AI 日报 - 2026年07月01日"', markdown)
        self.assertIn("date: 2026-07-01", markdown)


if __name__ == "__main__":
    unittest.main()
