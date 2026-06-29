import importlib.util
import pathlib
import tempfile
import unittest


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


if __name__ == "__main__":
    unittest.main()
