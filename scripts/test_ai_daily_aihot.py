import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from scripts.ai_daily_aihot import AIHOTSource
from scripts.ai_daily_editorial import editorial_context, load_profile, prioritize_items
from scripts.ai_daily_evidence import review_evidence
from scripts.ai_daily_history import prepare_history, read_history
from scripts.ai_daily_quality import QualityMode, validate_report, validate_repair_or_fallback
from scripts.ai_daily_sources import CallableSource, SourceContext, SourceItem, SourceRegistry, SourceResult, SourceStatus, SourceTier
from scripts.test_generate_ai_daily import MODULE


ROOT = Path(__file__).resolve().parent.parent
DAY = date(2026, 11, 21)


def entry(identity="one", **changes):
    item = {
        "id": identity, "title": "AI Agent 文档工具", "summary": "AI Agent 工具新增文档导出功能。",
        "links": {"aihot": f"https://aihot.news/items/{identity}", "original": f"https://example.org/{identity}"},
        "source": {"name": "Example"}, "publishedAt": "2026-11-21T01:00:00Z",
        "discoveredAt": "2026-11-21T02:00:00Z", "category": "ai-products", "score": 80,
        "attribution": "AIHOT / Example",
    }
    item.update(changes)
    return item


def response(items=(), status=200, **headers):
    return Mock(status_code=status, headers=headers, json=lambda: {"items": list(items)})


class AIHOTTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.profile = load_profile(ROOT)

    def source(self, request):
        return AIHOTSource(self.profile, request=request, cache_dir=self.directory.name)

    def test_secondary_summary_keeps_original_for_identity_only(self):
        request = Mock(return_value=response([entry()]))
        item = self.source(request).fetch(SourceContext(DAY)).items[0]
        self.assertEqual(item.url, "https://aihot.news/items/one")
        self.assertEqual(item.metadata["original_url"], "https://example.org/one")
        self.assertEqual(item.source_tier, SourceTier.AGGREGATOR)
        self.assertEqual(item.metadata["material_kind"], "provider_summary")
        self.assertNotIn("score", item.engagement)
        raw = MODULE.format_raw_data(MODULE.source_results_to_legacy({"AIHOT": SourceResult("AIHOT", SourceStatus.ACTIVE, [item])}))
        self.assertIn("二手摘要：AIHOT", raw)
        self.assertIn("主线匹配提示=", raw)
        self.assertNotIn(item.metadata["original_url"], raw)
        request.assert_called_once()

    def test_cache_reuses_fresh_body_and_revalidates_304(self):
        request = Mock(side_effect=[response([entry()], ETag='W/"one"', **{"Cache-Control": "max-age=60"}), response(status=304)])
        source = self.source(request)
        with patch("scripts.ai_daily_aihot.time.time", return_value=1000):
            first = source.fetch(SourceContext(DAY))
            second = source.fetch(SourceContext(DAY))
        self.assertEqual(request.call_count, 1)
        with patch("scripts.ai_daily_aihot.time.time", return_value=1061):
            third = source.fetch(SourceContext(DAY))
        self.assertEqual(first.items[0].summary, second.items[0].summary)
        self.assertEqual(first.items[0].summary, third.items[0].summary)
        self.assertEqual(request.call_args.kwargs["headers"]["If-None-Match"], 'W/"one"')

    def test_failure_is_optional_and_never_retried_early(self):
        for reply in (response(status=304), response(status=429, **{"Retry-After": "120"}), response(status=503)):
            with self.subTest(status=reply.status_code):
                request = Mock(return_value=reply)
                self.assertEqual(self.source(request).fetch(SourceContext(DAY)).status, SourceStatus.FAILED)
                request.assert_called_once()
        request = Mock(side_effect=requests.Timeout())
        self.assertEqual(self.source(request).fetch(SourceContext(DAY)).status, SourceStatus.FAILED)

    def test_invalid_cache_and_no_store_do_not_drop_valid_api_response(self):
        request = Mock(return_value=response([entry()], **{"Cache-Control": "no-store"}))
        source = self.source(request)
        source.cache_path.write_text('{"url":"invalid","payload":null}', encoding="utf-8")
        self.assertEqual(source.fetch(SourceContext(DAY)).status, SourceStatus.ACTIVE)
        self.assertFalse(source.cache_path.exists())
        with patch("scripts.ai_daily_aihot.tempfile.NamedTemporaryFile", side_effect=PermissionError()):
            source = self.source(Mock(return_value=response([entry()])))
            self.assertEqual(source.fetch(SourceContext(DAY)).status, SourceStatus.ACTIVE)

    def test_unknown_old_future_dates_are_not_promoted_by_discovery_time(self):
        records = [entry("unknown", publishedAt=None), entry("old", publishedAt="2026-10-01"),
                   entry("future", publishedAt="2026-11-22"), entry("fresh")]
        result = self.source(Mock(return_value=response(records))).fetch(SourceContext(DAY))
        self.assertIsNone(next(item for item in result.items if item.metadata["aihot_id"] == "unknown").published_at)
        with patch.object(MODULE, "CONTENT_DIR", Path(self.directory.name)):
            MODULE.filter_source_results({"AIHOT": result}, DAY)
        self.assertEqual([item.metadata["aihot_id"] for item in result.items], ["fresh"])
        request = Mock()
        self.assertEqual(self.source(request).fetch(SourceContext(DAY, historical=True)).status, SourceStatus.SKIPPED)
        request.assert_not_called()

    def test_profile_drives_ranking_and_keeps_unmatched_candidates(self):
        unrelated = entry("opinion", title="行业观察", summary="关于行业未来的观点。", category="opinion", score=100)
        tutorial = entry("tutorial", title="MCP 教程", summary="MCP 集成的操作方法。", category="tip", score=10)
        result = self.source(Mock(return_value=response([unrelated, tutorial]))).fetch(SourceContext(DAY, limit=1))
        self.assertEqual(result.items[0].metadata["aihot_id"], "tutorial")
        items = self.source(Mock(return_value=response([unrelated, tutorial]))).fetch(SourceContext(DAY)).items
        self.assertEqual(len(items), 2)
        changed = copy.deepcopy(self.profile)
        changed["missions"] = [{"name": "行业研究", "purpose": "关注行业", "topics": ["行业"]}]
        self.assertEqual(prioritize_items(items, changed)[0].metadata["aihot_id"], "opinion")
        self.assertIn("行业研究：关注行业", editorial_context(changed))
        self.assertIn(editorial_context(self.profile), MODULE.ANALYSIS_SYSTEM_PROMPT)
        changed["aihot"]["enabled"] = False
        self.assertNotIn("AIHOT", [adapter.name for adapter in MODULE.build_source_registry(editorial_profile=changed).adapters])

    def test_official_source_wins_same_original_and_history_aliases_work(self):
        item = self.source(Mock(return_value=response([entry()]))).fetch(SourceContext(DAY)).items[0]
        official = CallableSource("OpenAI", SourceTier.OFFICIAL, lambda _: [{"title": "Different title", "url": item.metadata["original_url"]}])
        result = SourceRegistry([official, self.source(Mock(return_value=response([entry()])))]).fetch_all(SourceContext(DAY))
        self.assertEqual(len(result["OpenAI"].items), 1)
        self.assertEqual(result["AIHOT"].items, [])
        history = [{"id": "yesterday:1", "date": "2026-11-20", "urls": [item.metadata["original_url"]], "event_key": "other", "sources": []}]
        self.assertEqual(prepare_history([item], history, DAY), [])

    def test_evidence_requires_attribution_and_only_allows_collected_url(self):
        item = self.source(Mock(return_value=response([entry()]))).fetch(SourceContext(DAY)).items[0]
        report = f"## 01 今日变化\n\n1. **文档功能**\n据 AIHOT 整理，AI Agent 工具新增文档导出功能。[来源]({item.url})\n"
        self.assertTrue(validate_report(report, [item]).valid)
        self.assertFalse(validate_report(report.replace("据 AIHOT 整理，", ""), [item]).valid)
        self.assertFalse(validate_report(report.replace(item.url, item.metadata["original_url"]), [item]).valid)
        reply = {"items": [{"id": "1", "supported": True, "citations": [{"url": item.url, "quote": item.summary}], "previousIds": [], "newInformation": ""}]}
        bindings, issues = review_evidence(report, [item], lambda _: json.dumps(reply, ensure_ascii=False))
        self.assertFalse(issues)
        raw = MODULE.generate_markdown(report, "2026-11-20", evidence=bindings)
        path = Path(self.directory.name) / "2026-11-20.md"
        path.write_text(raw, encoding="utf-8")
        history = read_history(path.parent, DAY)
        self.assertIn(item.metadata["original_url"], history[0]["urls"])
        original = SourceItem("OpenAI", "Entirely different wording", item.metadata["original_url"])
        self.assertEqual(prepare_history([original], history, DAY), [])
        path.write_text(raw.replace("文档功能", "改写标题"), encoding="utf-8")
        self.assertNotIn(item.metadata["original_url"], read_history(path.parent, DAY)[0]["urls"])

    def test_fresh_aihot_story_can_trigger_editor_with_reachable_empty_core(self):
        item = self.source(Mock(return_value=response([entry()]))).fetch(SourceContext(DAY)).items[0]
        results = {name: SourceResult(name, SourceStatus.SKIPPED) for name in MODULE.CORE_SOURCES}
        results["AIHOT"] = SourceResult("AIHOT", SourceStatus.ACTIVE, [item])
        with patch.object(MODULE, "CONTENT_DIR", Path(self.directory.name)), \
             patch.object(MODULE, "refresh_opportunities"), patch.object(MODULE, "build_source_registry") as registry, \
             patch.object(MODULE, "call_llm", return_value=None) as analyze:
            registry.return_value.fetch_all.return_value = results
            self.assertEqual(MODULE._run_generation(MODULE.parse_args(["--dry-run", "--date", DAY.isoformat()])), 0)
            analyze.assert_called_once()
            analyze.reset_mock()
            for name in MODULE.CORE_SOURCES:
                results[name] = SourceResult(name, SourceStatus.FAILED, error="offline")
            registry.return_value.fetch_all.return_value = results
            self.assertEqual(MODULE._run_generation(MODULE.parse_args(["--dry-run", "--date", DAY.isoformat()])), 1)
            analyze.assert_not_called()

    def test_failed_duplicate_repair_keeps_one_auditable_item(self):
        item = self.source(Mock(return_value=response([entry()]))).fetch(SourceContext(DAY)).items[0]
        block = f"1. **文档功能**\n据 AIHOT 整理，AI Agent 工具新增文档导出功能。[来源]({item.url})\n"
        report = "## 01 今日变化\n\n" + block + "\n## 03 办公落地\n\n" + block
        reply = {"items": [{"id": "1", "supported": True, "citations": [{"url": item.url, "quote": item.summary}], "previousIds": [], "newInformation": ""}]}
        result = validate_repair_or_fallback(report, {"AIHOT": SourceResult("AIHOT", SourceStatus.ACTIVE, [item])},
            target_date=DAY, repair=lambda _: report, audit=lambda _: json.dumps(reply, ensure_ascii=False))
        self.assertEqual(result.mode, QualityMode.REPAIRED)
        self.assertEqual(len(result.bindings), 1)
        self.assertNotIn("## 03", result.content)


if __name__ == "__main__":
    unittest.main()
