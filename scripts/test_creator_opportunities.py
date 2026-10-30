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


if __name__ == "__main__":
    unittest.main()
