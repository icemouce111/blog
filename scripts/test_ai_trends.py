import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.ai_trends import (
    refresh_trends,
    should_refresh,
    validate_insight_sources,
)


class AiTrendRefreshTest(unittest.TestCase):
    def test_window_thresholds_and_cadence(self):
        self.assertFalse(should_refresh("week", coverage_count=3, age_days=30))
        self.assertTrue(should_refresh("week", coverage_count=4, age_days=1))
        self.assertFalse(should_refresh("month", coverage_count=13, age_days=30))
        self.assertTrue(should_refresh("month", coverage_count=14, age_days=7))
        self.assertTrue(should_refresh("year", coverage_count=60, age_days=30))

    def test_rejects_sources_outside_archive_whitelist(self):
        allowed = {"https://example.com/known"}
        candidate = {
            "sources": [{"title": "Unknown", "url": "https://example.com/invented"}]
        }

        self.assertFalse(validate_insight_sources(candidate, allowed))

    def test_accepts_nonempty_sources_from_archive_whitelist(self):
        allowed = {"https://example.com/known"}
        candidate = {
            "sources": [{"title": "Known", "url": "https://example.com/known"}]
        }

        self.assertTrue(validate_insight_sources(candidate, allowed))

    def test_refreshes_eligible_window_with_archive_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "content"
            content.mkdir()
            for day in range(26, 30):
                (content / f"2026-06-{day}.md").write_text(
                    f"# Daily\nhttps://example.com/{day}\n",
                    encoding="utf-8",
                )
            snapshot = root / "trends.json"
            snapshot.write_text(json.dumps({
                "windows": [{
                    "window": "week",
                    "updatedAt": "2026-06-20T00:00:00+00:00",
                }]
            }), encoding="utf-8")
            output = {
                "insights": [{
                    "title": f"趋势 {index}",
                    "summary": "有档案来源支持的应用趋势判断。",
                    "sources": [{
                        "title": "Known",
                        "url": "https://example.com/29",
                    }],
                } for index in range(1, 4)]
            }

            changed = refresh_trends(
                content,
                snapshot,
                lambda _prompt: json.dumps(output, ensure_ascii=False),
                now=datetime(2026, 6, 29, 12, tzinfo=timezone.utc),
            )
            saved = json.loads(snapshot.read_text(encoding="utf-8"))

            self.assertTrue(changed)
            self.assertEqual(saved["windows"][0]["mode"], "generated")
            self.assertEqual(saved["windows"][0]["coverageCount"], 4)
            self.assertEqual(
                saved["windows"][0]["insights"][0]["sources"][0]["publishedAt"],
                "2026-06-29",
            )

    def test_preserves_snapshot_when_generated_sources_are_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "content"
            content.mkdir()
            for day in range(26, 30):
                (content / f"2026-06-{day}.md").write_text(
                    f"# Daily\nhttps://example.com/{day}\n",
                    encoding="utf-8",
                )
            snapshot = root / "trends.json"
            original = {
                "windows": [{
                    "window": "week",
                    "updatedAt": "2026-06-20T00:00:00+00:00",
                    "insights": [],
                }]
            }
            snapshot.write_text(json.dumps(original), encoding="utf-8")
            output = {
                "insights": [{
                    "title": f"趋势 {index}",
                    "summary": "来源不在白名单。",
                    "sources": [{
                        "title": "Unknown",
                        "url": "https://example.com/invented",
                    }],
                } for index in range(1, 4)]
            }

            changed = refresh_trends(
                content,
                snapshot,
                lambda _prompt: json.dumps(output),
                now=datetime(2026, 6, 29, 12, tzinfo=timezone.utc),
            )

            self.assertFalse(changed)
            self.assertEqual(
                json.loads(snapshot.read_text(encoding="utf-8")),
                original,
            )


if __name__ == "__main__":
    unittest.main()
