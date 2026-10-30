import copy
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from scripts import creator_opportunities as radar


TODAY = datetime.now(radar.CST).date()
PROFILE = {"followersBelow": 1000, "weeklyHours": 10, "verificationMaxAgeDays": 7}
CONFIG = {
    "profile": PROFILE, "officialHosts": ["official.example", "bilibili.com"],
    "limits": {"searchQueries": 1, "pagesPerRun": 4, "newCandidates": 2, "timeoutSeconds": 1},
    "discoveryQueries": ["{year} {month} AI创作奖励"], "watchSources": [],
}


def opportunity(**changes):
    item = {
        "id": "sample", "title": "AI商品短片", "organizer": "官方主办", "type": "创作赛",
        "url": "https://official.example/activity/sample", "rewardTypes": ["cash_prize"],
        "reward": "现金奖金100元，评优非保底", "requirements": "原创视频至少30秒，需申请审核",
        "deadline": str(TODAY + timedelta(days=10)), "deadlineKind": "dated",
        "deadlineText": "具体时间以规则为准", "fitStage": "apply", "fit": "可积累商品样片和教程",
        "minFollowers": None, "priority": 1, "verification": "official",
        "verifiedAt": str(TODAY), "checkedAt": None,
    }
    return dict(item, **changes)


def page_for(item, text=None, hash_value="fresh"):
    return {"id": item["id"], "url": item["url"], "ok": True,
            "text": text or f"现金奖金100元，评优非保底。原创视频至少30秒，需申请审核。截止{item['deadline']}。",
            "hash": hash_value, "links": []}


def extracted(item):
    result = copy.deepcopy(item)
    result["evidence"] = {"reward": "现金奖金100元，评优非保底", "requirements": "原创视频至少30秒，需申请审核",
                          "deadline": "截止" + item["deadline"]}
    return result


class OpportunityPolicyTest(unittest.TestCase):
    def test_eligibility_and_uncertainty_are_separate(self):
        cases = [({}, "recommended"), ({"minFollowers": 1000}, "later"),
                 ({"fitStage": "later"}, "later"), ({"verification": "pending"}, "pending"),
                 ({"deadline": None, "deadlineKind": "unknown"}, "pending"),
                 ({"deadline": None, "deadlineKind": "conflicting"}, "pending"),
                 ({"verifiedAt": str(TODAY - timedelta(days=8))}, "pending"),
                 ({"verifiedAt": str(TODAY + timedelta(days=1))}, "pending"),
                 ({"deadline": str(TODAY - timedelta(days=1))}, "expired")]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                self.assertEqual(radar.classify(opportunity(**changes), TODAY, PROFILE), expected)

    def test_ugc_host_is_not_official_rule_evidence(self):
        self.assertFalse(radar.automatic_review_url("https://www.bilibili.com/video/some-user-video", CONFIG))
        self.assertFalse(radar.official_url("https://official.example.evil.invalid/activity", CONFIG))
        self.assertFalse(radar.official_url("https://user:credential@official.example/activity", CONFIG))

    def test_rule_quotes_numbers_and_deadline_must_match(self):
        item = opportunity()
        page = page_for(item)
        self.assertIsNone(radar.validate_extraction(extracted(item), page, TODAY))
        for changes in [{"reward": "现金奖金999元"}, {"minFollowers": 0},
                        {"deadline": str(TODAY + timedelta(days=20))}, {"evidence": {}},
                        {"rewardTypes": ["unknown-reward"]}, {"fit": "粉丝数未设门槛，零粉可参加"}]:
            with self.subTest(changes=changes):
                candidate = dict(extracted(item), **changes)
                self.assertIsNotNone(radar.validate_extraction(candidate, page, TODAY))

    def test_credits_cannot_be_relabelled_as_cash(self):
        item = opportunity(reward="奖励100积分")
        candidate = extracted(item)
        candidate["evidence"]["reward"] = "奖励100积分，优秀创作者可获资源"
        self.assertIsNotNone(radar.validate_extraction(candidate, page_for(item, "奖励100积分，优秀创作者可获资源。原创视频至少30秒，需申请审核。截止" + item["deadline"]), TODAY))

    def test_numeric_units_are_normalized_but_substrings_are_not_evidence(self):
        self.assertEqual(radar.number_tokens("1万播放，奖金1.2万元"), {"10000", "12000"})
        candidate = extracted(opportunity(reward="现金奖金10元"))
        self.assertIsNotNone(radar.validate_extraction(candidate, page_for(opportunity()), TODAY))

    def test_yearless_deadline_cannot_silently_turn_an_old_event_into_this_year(self):
        item = opportunity()
        candidate = extracted(item)
        deadline = radar.iso_date(item['deadline'])
        quote = f"活动截止{deadline.month}月{deadline.day}日"
        candidate['evidence']['deadline'] = quote
        page = page_for(item)
        page['text'] += quote
        self.assertIsNotNone(radar.validate_extraction(candidate, page, TODAY))

    def test_nextjs_text_is_decoded_without_running_javascript(self):
        chunk = json.dumps({"content": "<p>AI创作活动：现金奖金100元</p>"}, ensure_ascii=False)
        script = "self.__next_f.push(" + json.dumps([1, chunk]) + ")"
        text, links = radar.page_text('<script>' + script + '</script><a href="/activity/72">AI创作活动</a>')
        self.assertIn("现金奖金100元", text)
        self.assertIn(("AI创作活动", "/activity/72"), links)

    def test_closed_directory_entries_are_not_discovered_as_current_leads(self):
        _, links = radar.page_text('<ul><li><a href="/past">AI创作大赛</a> 征集已结束</li><li><a href="/current">AI挑战</a> 作品征集中</li></ul>')
        self.assertEqual(links, [("AI挑战", "/current")])

    def test_multiple_field_quotes_support_only_their_own_numbers(self):
        item = opportunity(reward="现金奖金100元，个人奖20元")
        candidate = extracted(item)
        candidate["evidence"]["reward"] = ["现金奖金100元，评优非保底", "个人奖20元，择优评定"]
        page = page_for(item)
        page["text"] += "个人奖20元，择优评定"
        self.assertIsNone(radar.validate_extraction(candidate, page, TODAY))
        candidate["reward"] = "现金奖金100元，个人奖30元"
        self.assertIsNotNone(radar.validate_extraction(candidate, page, TODAY))

    def test_flight_text_records_do_not_mix_other_events_locale_prizes(self):
        body = "AI活动细则：现金奖金100元，截止2026-11-15。"
        chunk = '8a:T' + format(len(body.encode()), 'x') + ',' + body
        source = json.dumps([1, chunk], ensure_ascii=False)
        escaped = source.replace('\\', '\\\\').replace('"', '\\"')
        text, _ = radar.page_text('<script>self.__next_f.push(' + escaped + ')</script>')
        self.assertIn(body, text)

    def test_checked_in_snapshot_has_valid_contract(self):
        root = Path(__file__).resolve().parent.parent
        radar.validate_snapshot(json.loads((root / radar.DATA_PATH).read_text()), json.loads((root / radar.CONFIG_PATH).read_text()))


class RefreshTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / radar.DATA_PATH).parent.mkdir(parents=True)
        (self.root / radar.CONFIG_PATH).write_text(json.dumps(CONFIG))
        self.item = opportunity()
        self.save([self.item])
        self.search = Mock(return_value=[])

    def save(self, items):
        (self.root / radar.DATA_PATH).write_text(json.dumps({"schemaVersion": 2, "updatedAt": str(TODAY), "collection": {}, "opportunities": items}))

    def run_refresh(self, **kwargs):
        defaults = {"search": self.search, "fetch": lambda url, config: page_for(self.item),
                    "extract": lambda pages, ref: [extracted(self.item)], "dry_run": True}
        return radar.refresh_opportunities(self.root, TODAY, **(defaults | kwargs))

    def test_discovery_is_separate_from_official_verification(self):
        self.search.return_value = [{"title": "AI创作现金活动", "url": "https://thirdparty.example/activity"}]
        result = self.run_refresh()
        new = [item for item in result["opportunities"] if item["id"] != "sample"][0]
        self.assertEqual(new["verification"], "pending")
        self.assertEqual(new["url"], "")
        self.assertEqual(new["sourceUrl"], "https://thirdparty.example/activity")
        self.assertEqual(result["collection"]["discovered"], 1)

    def test_dry_run_keeps_snapshot_unchanged(self):
        path = self.root / radar.DATA_PATH
        before = path.read_bytes()
        result = self.run_refresh()
        self.assertEqual(result["collection"]["verified"], 1)
        self.assertEqual(path.read_bytes(), before)

    def test_changed_rule_and_model_failure_cannot_keep_verified_status(self):
        self.item["sourceHash"] = "old"
        self.save([self.item])
        result = self.run_refresh(extract=Mock(side_effect=RuntimeError("synthetic failure")))
        self.assertEqual(result["opportunities"][0]["verification"], "pending")
        self.assertEqual(result["collection"]["modelStatus"], "failed")

    def test_source_failure_does_not_renew_a_previous_verification(self):
        self.item["verifiedAt"] = str(TODAY - timedelta(days=1))
        self.save([self.item])
        result = self.run_refresh(fetch=lambda url, config: {"ok": False, "url": url})
        actual = result["opportunities"][0]
        self.assertEqual(actual["verifiedAt"], self.item["verifiedAt"])
        self.assertEqual(actual["verification"], "pending")

    def test_unchanged_previously_verified_rule_is_rechecked_without_model_cost(self):
        self.item["sourceHash"] = "fresh"
        self.item["verifiedAt"] = str(TODAY - timedelta(days=1))
        self.save([self.item])
        extract = Mock()
        result = self.run_refresh(extract=extract)
        self.assertEqual(result["opportunities"][0]["verifiedAt"], str(TODAY))
        extract.assert_not_called()

    def test_daily_rerun_is_idempotent_after_a_scanned_write(self):
        with patch.object(radar, "scan_files") as scan:
            result = self.run_refresh(dry_run=False)
        scan.assert_called_once()
        unused = Mock(side_effect=AssertionError("must not run twice"))
        repeated = self.run_refresh(search=unused, fetch=unused, extract=unused)
        self.assertEqual(repeated, result)

    def test_historical_runs_never_collect_future_opportunities(self):
        unused = Mock(side_effect=AssertionError("historical fetch"))
        result = radar.refresh_opportunities(self.root, TODAY - timedelta(days=1), search=unused, fetch=unused, extract=unused)
        self.assertEqual(result["collection"], {})

    def test_search_failure_is_explicit_and_does_not_stop_news(self):
        result = self.run_refresh(search=Mock(side_effect=TimeoutError()))
        self.assertEqual(result["collection"]["searchFailures"], 1)
        self.assertEqual(result["collection"]["verified"], 1)

    def test_malformed_model_entries_are_ignored_without_stopping_news(self):
        result = self.run_refresh(extract=lambda pages, ref: [{"id": []}, dict(extracted(self.item), rewardTypes=[{}])])
        self.assertEqual(result["collection"]["verified"], 0)


class TargetedDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        config_path = Path(__file__).resolve().parent.parent / radar.CONFIG_PATH
        self.config = json.loads(config_path.read_text())
        self.config['watchSources'] = []
        self.config['discoverySources'] = []
        self.config['limits']['newCandidates'] = 5
        self.config['discoveryQueries'] = ['{year} {month} AI创作者激励', 'AI商家合作']
        (self.root / radar.DATA_PATH).parent.mkdir(parents=True)
        (self.root / radar.DATA_PATH).write_text(json.dumps({
            'schemaVersion': 2, 'updatedAt': str(TODAY), 'collection': {}, 'opportunities': []}))
        self.write_config()

    def write_config(self):
        (self.root / radar.CONFIG_PATH).write_text(json.dumps(self.config))

    def refresh(self, search, **kwargs):
        fetch = Mock(side_effect=AssertionError('social posts must not be fetched as official rules'))
        extract = Mock(side_effect=AssertionError('social posts must not be verified by the model'))
        reference = kwargs.pop('reference', TODAY)
        result = radar.refresh_opportunities(self.root, reference, search=search, fetch=fetch,
                                            extract=extract, dry_run=kwargs.pop('dry_run', True), **kwargs)
        fetch.assert_not_called()
        extract.assert_not_called()
        return result

    def test_each_platform_keeps_two_queries_before_general_discovery(self):
        plan = radar.discovery_plan(self.config, TODAY)
        self.assertEqual(len(plan), 10)
        for key in ('xiaohongshu', 'douyin', 'x', 'wechat'):
            self.assertEqual(sum(item['channel'] == key for item in plan), 2)
        self.assertEqual([item['channel'] for item in plan[:4]], ['xiaohongshu', 'douyin', 'x', 'wechat'])
        self.assertEqual(sum(item['channel'] == 'general' for item in plan), 2)
        self.assertNotIn('{year}', str(plan))
        self.config['limits']['searchQueries'] = 4
        with self.assertRaises(ValueError):
            radar.discovery_plan(self.config, TODAY)

    def test_named_campaigns_and_non_cash_programs_are_not_filtered_out(self):
        for title in ('AI替我说', 'AI 替我说知识共创', '用AI讲知识', 'vibe知识大赏',
                      '公众号征稿', '创作基金', 'creator program', 'AI bounties', 'paid collaboration'):
            with self.subTest(title=title):
                self.assertTrue(radar.LEAD_WORDS.search(title))
        self.assertIsNone(radar.LEAD_WORDS.search('Learn how to make a video'))

    def test_busy_platform_cannot_starve_other_platforms(self):
        def search(query, _timeout):
            if 'site:xiaohongshu.com' in query:
                return [{'title': 'AI替我说', 'url': f'https://www.xiaohongshu.com/explore/{index}'} for index in range(10)]
            if 'site:douyin.com' in query:
                return [{'title': 'vibe知识大赏', 'url': 'https://www.douyin.com/video/one'}]
            if 'site:x.com' in query:
                return [{'title': 'AI creator program', 'url': 'https://x.com/creator/status/one'}]
            if 'site:mp.weixin.qq.com' in query:
                return [{'title': '公众号AI征稿', 'url': 'https://mp.weixin.qq.com/s/one'}]
            return []
        result = self.refresh(search)
        items = result['opportunities']
        self.assertEqual(len(items), 5)
        self.assertEqual({item['discoveryPlatform'] for item in items}, {'xiaohongshu', 'douyin', 'x', 'wechat'})
        self.assertTrue(all(item['verification'] == 'pending' and item['url'] == '' and item['reviewMode'] == 'manual' for item in items))
        self.assertEqual(len(result['collection']['reviewQueue']), 5)

    def test_platform_host_never_becomes_official_authority(self):
        for channel in self.config['platformChannels']:
            for host in channel['hosts']:
                url = f'https://{host}/post/example'
                self.assertEqual(radar.platform_for_url(url, self.config), channel['id'])
                self.assertFalse(radar.official_url(url, self.config))
                self.assertIsNone(radar.platform_for_url(f'https://{host}.evil.example/post', self.config))

    def test_search_engine_ignoring_site_filters_does_not_fake_platform_coverage(self):
        result = self.refresh(lambda query, timeout: [{'title': 'AI创作者活动', 'url': 'https://elsewhere.example/event'}])
        self.assertEqual(len(result['opportunities']), 1)  # general searches may retain a second-hand lead
        self.assertNotIn('discoveryPlatform', result['opportunities'][0])
        for metric in result['collection']['channels'].values():
            self.assertEqual(metric['completed'], 2)
            self.assertEqual(metric['leads'], 0)
            self.assertEqual(metric['discovered'], 0)

    def test_failure_is_reported_for_its_platform_without_stopping_other_searches(self):
        def search(query, _timeout):
            if 'site:x.com' in query or '推特' in query:
                raise TimeoutError()
            return []
        result = self.refresh(search)
        self.assertEqual(result['collection']['channels']['x']['failures'], 2)
        self.assertEqual(result['collection']['channels']['wechat']['completed'], 2)
        self.assertEqual(result['collection']['searches'], 8)
        self.assertEqual(result['collection']['searchFailures'], 2)

    def test_platform_specific_secondary_report_stays_a_manual_lead(self):
        def search(query, _timeout):
            return [{'title': 'AI替我说知识共创', 'url': 'https://report.example/ai-program'}] if '小红书' in query else []
        result = self.refresh(search)
        item = result['opportunities'][0]
        self.assertEqual(item['discoveryPlatform'], 'xiaohongshu')
        self.assertEqual(item['verification'], 'pending')
        self.assertEqual(item['sourceUrl'], 'https://report.example/ai-program')
        self.assertEqual(item['url'], '')
        self.assertEqual(result['collection']['channels']['xiaohongshu']['platformLeads'], 0)
        self.assertGreater(result['collection']['channels']['xiaohongshu']['secondaryLeads'], 0)

    def test_full_queue_keeps_new_discoveries_and_curated_records(self):
        old = [opportunity(id=f'discovered-old-{i}', verification='pending', url='',
                           sourceUrl=f'https://report.example/old/{i}',
                           discoveredAt=str(TODAY-timedelta(days=30))) for i in range(100)]
        curated = opportunity(id='curated', verification='pending', url='', sourceUrl='https://report.example/curated')
        path = self.root / radar.DATA_PATH
        data = json.loads(path.read_text())
        data['opportunities'] = old + [curated]
        path.write_text(json.dumps(data))
        result = self.refresh(lambda q, t: [{'title':'AI征稿', 'url':'https://report.example/new'}])
        self.assertEqual(len(result['opportunities']), 100)
        self.assertIn('curated', {item['id'] for item in result['opportunities']})
        self.assertIn('https://report.example/new', {item.get('sourceUrl') for item in result['opportunities']})

    def test_malformed_search_payload_is_counted_as_failure(self):
        result = self.refresh(lambda q, t: None)
        self.assertEqual(result['collection']['searches'], 0)
        self.assertEqual(result['collection']['searchFailures'], 10)

    def test_source_change_invalidates_same_day_cache(self):
        with patch.object(radar, 'scan_files'):
            self.refresh(lambda q, t: [], dry_run=False)
        self.config['platformChannels'][0]['queries'].append('site:xiaohongshu.com 新的共创计划')
        self.write_config()
        search = Mock(return_value=[])
        self.refresh(search)
        self.assertEqual(search.call_count, 2)  # config refresh does not bypass the platform interval

    def test_platform_search_runs_every_three_days_and_preserves_previous_dates(self):
        with patch.object(radar, 'scan_files'):
            first_search = Mock(return_value=[])
            first = self.refresh(first_search, dry_run=False)
            self.assertEqual(first_search.call_count, 10)
            for offset in (1, 2):
                search = Mock(return_value=[])
                result = self.refresh(search, reference=TODAY+timedelta(days=offset), dry_run=False)
                self.assertEqual(search.call_count, 2)  # daily general discovery still runs
                for key, metric in result['collection']['channels'].items():
                    self.assertTrue(metric['skipped'])
                    self.assertEqual(metric['lastSearchedAt'], str(TODAY))
                    self.assertEqual(metric['nextSearchAt'], str(TODAY+timedelta(days=3)))
                    self.assertEqual(metric['completed'], first['collection']['channels'][key]['completed'])
            search = Mock(return_value=[])
            result = self.refresh(search, reference=TODAY+timedelta(days=3))
            self.assertEqual(search.call_count, 10)
            self.assertTrue(all(not m['skipped'] for m in result['collection']['channels'].values()))

    def test_forcing_a_daily_report_does_not_bypass_platform_interval(self):
        with patch.object(radar, 'scan_files'):
            self.refresh(lambda q,t: [], dry_run=False)
        search = Mock(return_value=[])
        self.refresh(search, force=True)
        self.assertEqual(search.call_count, 2)

    def test_failed_platform_attempt_also_observes_the_three_day_interval(self):
        with patch.object(radar, 'scan_files'):
            self.refresh(Mock(side_effect=TimeoutError()), dry_run=False)
        search = Mock(return_value=[])
        result = self.refresh(search, reference=TODAY+timedelta(days=1))
        self.assertEqual(search.call_count, 2)
        self.assertEqual(result['collection']['channels']['x']['failures'], 2)
        self.assertTrue(result['collection']['channels']['x']['skipped'])
        self.assertEqual(result['collection']['searchFailures'], 0)

    def test_old_channel_metrics_use_the_previous_collection_date(self):
        with patch.object(radar, 'scan_files'):
            self.refresh(lambda q,t: [], dry_run=False)
        path = self.root / radar.DATA_PATH
        data = json.loads(path.read_text())
        for metric in data['collection']['channels'].values():
            metric.pop('lastSearchedAt')
            metric.pop('nextSearchAt')
        path.write_text(json.dumps(data))
        search = Mock(return_value=[])
        result = self.refresh(search, reference=TODAY+timedelta(days=1))
        self.assertEqual(search.call_count, 2)
        self.assertEqual(result['collection']['channels']['wechat']['lastSearchedAt'], str(TODAY))

    def test_incidental_general_hit_does_not_rewrite_previous_platform_statistics(self):
        with patch.object(radar, 'scan_files'):
            self.refresh(lambda q,t: [], dry_run=False)
        result = self.refresh(lambda q,t: [{'title':'AI替我说', 'url':'https://www.xiaohongshu.com/explore/new'}], reference=TODAY+timedelta(days=1))
        self.assertEqual(result['collection']['discovered'], 1)
        self.assertEqual(result['collection']['incidentalPlatformDiscoveries']['xiaohongshu'], 1)
        self.assertEqual(result['collection']['channels']['xiaohongshu']['discovered'], 0)
        self.assertEqual(result['collection']['channels']['xiaohongshu']['lastSearchedAt'], str(TODAY))

    def test_targeted_dry_run_does_not_write_public_data(self):
        before = (self.root / radar.DATA_PATH).read_bytes()
        self.refresh(lambda q, t: [])
        self.assertEqual((self.root / radar.DATA_PATH).read_bytes(), before)

    def test_ai_tiwoshuo_is_named_but_dates_and_cash_stay_unconfirmed(self):
        root = Path(__file__).resolve().parent.parent
        snapshot = json.loads((root / radar.DATA_PATH).read_text())
        item = next(item for item in snapshot['opportunities'] if item['id'] == 'xhs-ai-knowledge')
        self.assertIn('AI替我说', item['title'])
        self.assertEqual(item['deadlineKind'], 'unknown')
        self.assertEqual(item['verification'], 'pending')
        self.assertEqual(item['url'], '')
        self.assertTrue(item['sourceUrl'])


if __name__ == "__main__":
    unittest.main()
