import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from scripts.ai_daily_quality import QualityMode, validate_repair_or_fallback
from scripts.ai_daily_sources import SourceItem, SourceResult, SourceStatus, SourceTier
from scripts.ai_daily_history import prepare_history, read_history, material_hash


class EvidenceBindingTest(unittest.TestCase):
    def setUp(self):
        self.source = SourceItem(source='OpenAI', title='工具A更新', url='https://example.org/a',
                                 summary='工具A增加文件导出功能，最高奖励100元。',
                                 published_at='2026-07-01', source_tier=SourceTier.OFFICIAL)
        self.report = '## 01 今日变化\n\n1. **工具A更新**\n工具A最高奖励100元。[来源](https://example.org/a)\n'
        self.reply = {'items': [{'id': '1', 'supported': True,
                                 'citations': [{'url': self.source.url, 'quote': self.source.summary}],
                                 'previousIds': [], 'newInformation': ''}]}

    def run_review(self, reply, *, source=None, report=None, history=()):
        source = source or self.source
        calls = []
        def audit(prompt):
            calls.append(prompt)
            return reply if isinstance(reply, str) or reply is None else json.dumps(reply, ensure_ascii=False)
        result = validate_repair_or_fallback(report or self.report,
            {'OpenAI': SourceResult('OpenAI', SourceStatus.ACTIVE, [source])},
            target_date=date(2026, 7, 1), repair=None, audit=audit, history=list(history))
        return result, calls

    def test_valid_review_saves_exact_per_item_quotations_and_material_hash(self):
        result, calls = self.run_review(self.reply)
        self.assertEqual(result.mode, QualityMode.ORIGINAL)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.bindings[0]['sources'][0]['content_hash'], material_hash(self.source))
        self.assertEqual(result.bindings[0]['citations'][0]['quote'], self.source.summary)

    def test_title_only_material_never_calls_the_reviewer_or_enters_edited_copy(self):
        source = copy.deepcopy(self.source); source.summary = ''
        report = '## 01 今日变化\n\n1. **工具A更新**\n工具A更新。[来源](https://example.org/a)\n'
        result, calls = self.run_review(self.reply, source=source, report=report)
        self.assertEqual(result.mode, QualityMode.FALLBACK)
        self.assertEqual(calls, [])
        self.assertFalse(result.bindings)

    def test_bulleted_output_is_repaired_before_the_evidence_audit(self):
        audits = []
        repairs = []
        result = validate_repair_or_fallback(self.report.replace('1. **', '- **'),
            {'OpenAI': SourceResult('OpenAI', SourceStatus.ACTIVE, [self.source])},
            target_date=date(2026, 7, 1),
            repair=lambda prompt: repairs.append(prompt) or self.report,
            audit=lambda prompt: audits.append(prompt) or json.dumps(self.reply, ensure_ascii=False))
        self.assertEqual(result.mode, QualityMode.REPAIRED)
        self.assertEqual(len(repairs), 1)
        self.assertEqual(len(audits), 1)

    def test_unbound_editorial_text_cannot_bypass_item_audit(self):
        result, calls = self.run_review(self.reply, report='## 01 今日变化\n\n工具B已全面开放。\n\n' + self.report)
        self.assertEqual(result.mode, QualityMode.FALLBACK)
        self.assertFalse(calls)

    def test_title_only_item_is_pruned_before_auditing_the_remaining_items(self):
        title_only = SourceItem('OpenAI','只有标题','https://example.org/title-only')
        report = self.report + '\n2. **只有标题**\n产品已全面上线。[来源](https://example.org/title-only)\n'
        audits = []
        result = validate_repair_or_fallback(report,
            {'OpenAI': SourceResult('OpenAI', SourceStatus.ACTIVE, [self.source, title_only])},
            target_date=date(2026, 7, 1), repair=lambda _prompt: report,
            audit=lambda prompt: audits.append(prompt) or json.dumps(self.reply, ensure_ascii=False))
        self.assertEqual(result.mode, QualityMode.REPAIRED)
        self.assertNotIn(title_only.url, result.content)
        self.assertEqual(len(audits), 1)
        self.assertEqual(len(result.bindings), 1)

    def test_supported_flag_does_not_override_missing_forged_or_wrong_source_quotes(self):
        variants = []
        bad = copy.deepcopy(self.reply);bad['items'][0]['citations'][0]['quote'] = '这是来源里完全不存在的一段证据';variants.append(bad)
        bad = copy.deepcopy(self.reply);bad['items'][0]['citations'][0]['url'] = 'https://example.org/b';variants.append(bad)
        bad = copy.deepcopy(self.reply);bad['items'][0]['citations'] = [];variants.append(bad)
        bad = copy.deepcopy(self.reply);bad['items'][0]['supported'] = 1;variants.append(bad)
        # A real quote that omits the claimed reward is also insufficient.
        bad = copy.deepcopy(self.reply);bad['items'][0]['citations'][0]['quote'] = '工具A增加文件导出功能';variants.append(bad)
        for reply in variants:
            with self.subTest(reply=reply):
                result, _ = self.run_review(reply)
                self.assertEqual(result.mode, QualityMode.FALLBACK)

    def test_incomplete_duplicate_or_unavailable_audit_fails_closed(self):
        variants = [None, 'not JSON', {'items': []}]
        bad = copy.deepcopy(self.reply);bad['items'].append(copy.deepcopy(bad['items'][0]));variants.append(bad)
        for reply in variants:
            with self.subTest(reply=reply):
                result, _ = self.run_review(reply)
                self.assertEqual(result.mode, QualityMode.FALLBACK)

    def test_prior_event_requires_new_quoted_information_and_cannot_hide_its_history(self):
        self.source.metadata['previous_reports'] = ['2026-06-30:1']
        history = [{'id':'2026-06-30:1','text':'工具A新增导出。','quotes':['工具A增加文件导出功能']}]
        result, _ = self.run_review(self.reply, history=history)
        self.assertEqual(result.mode, QualityMode.FALLBACK)
        self.reply['items'][0].update(previousIds=['2026-06-30:1'],newInformation='最高奖励100元')
        result, _ = self.run_review(self.reply, history=history)
        self.assertEqual(result.mode, QualityMode.ORIGINAL)
        self.reply['items'][0]['newInformation'] = '工具A增加文件导出功能'
        result, _ = self.run_review(self.reply, history=history)
        self.assertEqual(result.mode, QualityMode.FALLBACK)

    def test_failed_semantic_audit_after_repair_is_not_retried_again(self):
        calls = []
        result = validate_repair_or_fallback('not Markdown',
            {'OpenAI': SourceResult('OpenAI', SourceStatus.ACTIVE, [self.source])},
            target_date=date(2026, 7, 1), repair=lambda _: self.report,
            audit=lambda prompt: calls.append(prompt) or None)
        self.assertEqual(result.mode, QualityMode.FALLBACK)
        self.assertEqual(len(calls), 1)


class PublicationHistoryTest(unittest.TestCase):
    def test_existing_standalone_and_bulleted_headings_keep_full_source_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '2026-06-30.md').write_text('''---
title: "历史日报"
date: 2026-06-30
---
## 01 今日变化

**既有无编号文章**
这里是事件正文。[来源](https://example.org/legacy)
https://example.org/second-source

- **来源归档条目**：这里是速览正文。
  [来源](https://example.org/archive)

## 02 其他变化
1. **原有编号文章**
   [来源](https://example.org/ordered)
''')
            history = read_history(root, date(2026, 7, 1))
            self.assertEqual(len(history), 3)
            urls = {url for entry in history for url in entry['urls']}
            self.assertEqual(urls, {'https://example.org/legacy', 'https://example.org/second-source',
                                   'https://example.org/archive', 'https://example.org/ordered'})
            item = SourceItem('OpenAI','不同标题','https://example.org/legacy',summary='同一旧闻。')
            self.assertEqual(prepare_history([item], history, date(2026, 7, 1)), [])

    def test_history_excludes_today_and_future_even_for_backfills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for day in ['2026-06-30','2026-07-01','2026-07-02']:
                (root / f'{day}.md').write_text('## 01 今日变化\n1. **AI工具** [来源](https://example.org/a)\n')
            history = read_history(root, date(2026, 7, 1))
            self.assertEqual([entry['date'] for entry in history], ['2026-06-30'])

    def test_same_story_on_a_new_url_is_flagged_for_incremental_review(self):
        previous = [{'id':'2026-06-30:1','date':'2026-06-30','event_key':'ai工具发布',
                     'urls':['https://example.org/a'],'sources':[]}]
        item = SourceItem('OpenAI','AI 工具发布','https://other.example/a',summary='重复报道。')
        selected = prepare_history([item], previous, date(2026, 7, 1))
        self.assertEqual(selected[0].metadata['previous_reports'], ['2026-06-30:1'])

    def test_counters_do_not_requalify_a_story_and_dated_material_change_does(self):
        item = SourceItem('OpenAI','AI工具发布','https://example.org/a',summary='新增导出功能。',published_at='2026-06-30')
        previous = [{'id':'2026-06-30:1','date':'2026-06-30','event_key':'ai工具发布',
                     'urls':[item.url],'sources':[{'url':item.url,'content_hash':material_hash(item)}]}]
        item.engagement['stars'] = 999
        item.metadata['updated_at'] = '2026-07-01T08:00:00+08:00'
        self.assertEqual(prepare_history([item],previous,date(2026,7,1)), [])
        item.summary = '新增文件导出与离线预览功能。'
        selected = prepare_history([item],previous,date(2026,7,1))
        self.assertEqual(selected[0].metadata['freshness_at'], '2026-07-01')

    def test_missing_or_malformed_legacy_hash_does_not_prove_a_material_update(self):
        item = SourceItem('OpenAI','AI工具发布','https://example.org/a',summary='新增离线功能。',
                          metadata={'updated_at':'2026-07-01T00:30:00+08:00'})
        for digest in [None, '', [], 'not-a-hash']:
            previous = [{'id':'2026-06-30:1','date':'2026-06-30','event_key':'ai工具发布',
                         'urls':[item.url],'sources':[{'url':item.url,'content_hash':digest}]}]
            self.assertEqual(prepare_history([item],previous,date(2026,7,1)), [])

    def test_update_time_uses_shanghai_calendar_day(self):
        item = SourceItem('OpenAI','AI工具发布','https://example.org/a',summary='新增导出功能。')
        previous = [{'id':'2026-06-30:1','date':'2026-06-30','event_key':'ai工具发布',
                     'urls':[item.url],'sources':[{'url':item.url,'content_hash':material_hash(item)}]}]
        item.summary = '新增导出与离线预览功能。'
        item.metadata['updated_at'] = '2026-06-30T16:30:00Z'
        self.assertEqual(prepare_history([item],previous,date(2026,7,1))[0].metadata['freshness_at'], '2026-07-01')

    def test_trend_opportunity_and_daily_snapshot_keep_their_existing_cadence(self):
        previous = [{'id':'2026-06-30:1','date':'2026-06-30','event_key':'ai工具',
                     'urls':['https://example.org/a'],'sources':[]}]
        for basis, signal in [('snapshot','story'),('deadline','opportunity'),('rolling','trend')]:
            item = SourceItem('Fixture','AI工具','https://example.org/a',metadata={'date_basis':basis,'signal_type':signal})
            self.assertEqual(prepare_history([item],previous,date(2026,7,1)),[item])
