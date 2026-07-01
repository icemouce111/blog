import unittest
from datetime import date

from scripts.ai_daily_quality import (
    QualityMode,
    filter_usable_items,
    validate_report,
    validate_repair_or_fallback,
)
from scripts.ai_daily_sources import (
    SourceItem,
    SourceResult,
    SourceStatus,
    SourceTier,
)


def official_item(**overrides):
    values = {
        "source": "OpenAI",
        "title": "OpenAI 发布新模型",
        "url": "https://openai.com/index/new-model",
        "summary": "官方发布说明。",
        "published_at": "2026-06-30",
        "source_tier": SourceTier.OFFICIAL,
    }
    values.update(overrides)
    return SourceItem(**values)


def community_item(**overrides):
    values = {
        "source": "Linux.do",
        "title": "社区讨论 AI 工具",
        "url": "https://linux.do/t/topic/123",
        "summary": "用户分享使用体验。",
        "published_at": "2026-06-30",
        "source_tier": SourceTier.COMMUNITY,
    }
    values.update(overrides)
    return SourceItem(**values)


def result_for(*items):
    return {
        "OpenAI": SourceResult(
            "OpenAI",
            SourceStatus.ACTIVE,
            [item for item in items if item.source == "OpenAI"],
        ),
        "Linux.do": SourceResult(
            "Linux.do",
            SourceStatus.ACTIVE,
            [item for item in items if item.source == "Linux.do"],
        ),
    }


class ItemFilterTest(unittest.TestCase):
    def test_filters_stale_future_and_invalid_items_without_blocking_good_items(self):
        items = [
            official_item(),
            official_item(
                title="旧闻",
                url="https://openai.com/index/old",
                published_at="2026-04-01",
            ),
            official_item(
                title="未来消息",
                url="https://openai.com/index/future",
                published_at="2026-07-10",
            ),
            official_item(title="无链接", url=""),
        ]

        usable = filter_usable_items(items, date(2026, 7, 1))

        self.assertEqual([item.title for item in usable], ["OpenAI 发布新模型"])


class ReportValidationTest(unittest.TestCase):
    def test_rejects_urls_not_present_in_collected_evidence(self):
        report = """## 01 📌 今日头条

1. **OpenAI 发布新模型**
   官方发布新模型。来源：https://invented.example/news
"""
        validation = validate_report(report, [official_item()])

        self.assertFalse(validation.valid)
        self.assertIn("invented.example", validation.issues[0])

    def test_requires_attribution_for_community_only_claims(self):
        unattributed = """## 01 📌 今日头条

1. **AI 工具出现问题**
   AI 工具存在严重问题。来源：https://linux.do/t/topic/123
"""
        attributed = """## 01 📌 今日头条

1. **社区讨论 AI 工具问题**
   据 Linux.do 用户讨论，部分用户遇到问题。来源：https://linux.do/t/topic/123
"""

        self.assertFalse(validate_report(unattributed, [community_item()]).valid)
        self.assertTrue(validate_report(attributed, [community_item()]).valid)

    def test_rejects_unsupported_superlatives(self):
        report = """## 01 📌 今日头条

1. **OpenAI 发布新模型**
   这是当前最快的模型。来源：https://openai.com/index/new-model
"""

        validation = validate_report(report, [official_item()])

        self.assertFalse(validation.valid)
        self.assertTrue(any("最快" in issue for issue in validation.issues))

    def test_requires_a_collected_source_url_for_every_numbered_item(self):
        report = """## 01 📌 今日头条

1. **OpenAI 发布新模型**
   官方发布了新模型，但这里没有来源链接。
"""

        validation = validate_report(report, [official_item()])

        self.assertFalse(validation.valid)
        self.assertTrue(any("has no source URL" in issue for issue in validation.issues))

    def test_rejects_metrics_not_present_in_evidence(self):
        unsupported = """## 01 📌 今日头条

1. **搜索热度上升**
   关键词搜索量上涨 120%。来源：https://openai.com/index/new-model
"""
        supported = """## 01 📌 今日头条

1. **模型效率提升**
   官方材料称效率提升 25%。来源：https://openai.com/index/new-model
"""
        evidence = official_item(summary="官方材料称效率提升 25%。")

        self.assertFalse(validate_report(unsupported, [evidence]).valid)
        self.assertTrue(validate_report(supported, [evidence]).valid)


class RepairFallbackTest(unittest.TestCase):
    def test_accepts_one_valid_repair(self):
        invalid = """## 01 📌 今日头条

1. **AI 工具问题**
   这是事实。来源：https://linux.do/t/topic/123
"""
        repaired = """## 01 📌 今日头条

1. **社区讨论 AI 工具**
   据 Linux.do 用户讨论，部分用户分享了使用体验。来源：https://linux.do/t/topic/123
"""
        calls = []

        result = validate_repair_or_fallback(
            invalid,
            result_for(community_item()),
            target_date=date(2026, 7, 1),
            repair=lambda prompt: calls.append(prompt) or repaired,
        )

        self.assertEqual(result.mode, QualityMode.REPAIRED)
        self.assertEqual(result.content, repaired)
        self.assertEqual(len(calls), 1)

    def test_falls_back_to_collected_links_when_repair_is_still_invalid(self):
        invalid = "No numbered sections. https://invented.example"

        result = validate_repair_or_fallback(
            invalid,
            result_for(official_item(), community_item()),
            target_date=date(2026, 7, 1),
            repair=lambda _prompt: invalid,
        )

        self.assertEqual(result.mode, QualityMode.FALLBACK)
        self.assertTrue(result.content.startswith("## 01 📡 原始信号归档"))
        self.assertIn("https://openai.com/index/new-model", result.content)
        self.assertIn("https://linux.do/t/topic/123", result.content)
        self.assertNotIn("invented.example", result.content)
        self.assertTrue(any("repair" in issue for issue in result.issues))
        self.assertTrue(
            validate_report(
                result.content,
                [official_item(), community_item()],
            ).valid
        )


if __name__ == "__main__":
    unittest.main()
