import json
import unittest

from scripts.ai_daily_sop import Publisher
from scripts.github_daily import (
    build_record,
    build_user_prompt,
    extract_json,
    publisher_artifacts,
    publisher_commit_message,
    publisher_remote_artifact,
    validate_payload,
)
from scripts.github_trending import TrendingRepo, parse_count, parse_trending_html

FIXTURE_HTML = """<html><body><main>
<article class="Box-row">
  <h2 class="h3"><a href="/owner/alpha"><span>owner / <span>alpha</span></span></a></h2>
  <p class="col-9">Alpha does things well</p>
  <div class="f6">
    <span itemprop="programmingLanguage">Python</span>
    <a href="/owner/alpha/stargazers">1,234</a>
    <a href="/owner/alpha/forks">56</a>
    <span class="float-sm-right">98 stars today</span>
  </div>
  <a class="topic-tag" href="/topics/ai">ai</a>
  <a class="topic-tag" href="/topics/tools">tools</a>
</article>
<article class="Box-row">
  <h2 class="h3"><a href="/beta/beta-tool"><span>beta / <span>beta-tool</span></span></a></h2>
  <div class="f6">
    <a href="/beta/beta-tool/stargazers">999</a>
  </div>
</article>
<article class="Box-row">
  <h2 class="h3"><a href="/topics/not-a-repo">topic link only</a></h2>
</article>
</main></body></html>"""


def make_repos() -> list[TrendingRepo]:
    return [
        TrendingRepo(
            rank=1,
            full_name="owner/alpha",
            url="https://github.com/owner/alpha",
            description="Alpha does things well",
            language="Python",
            stars=1234,
            stars_today=98,
            topics=["ai", "tools"],
        ),
        TrendingRepo(
            rank=2,
            full_name="beta/beta-tool",
            url="https://github.com/beta/beta-tool",
            description="",
            language="",
        ),
    ]


def make_payload() -> dict:
    return {
        "intro": "今日榜单风向：AI 工具链继续升温。",
        "repos": [
            {"repo": "owner/alpha", "what": "一个做 X 的工具。", "help": "适合你练手。", "how": "先跑示例。"},
            {"repo": "beta/beta-tool", "what": "一个做 Y 的库。", "help": "可跳过。", "how": "收藏即可。"},
        ],
        "highlights": [
            {
                "repo": "owner/alpha",
                "title": "今日最值得关注",
                "why": "增长快",
                "value": "能直接用到项目里",
                "how": "先读 README 跑示例",
            },
            {
                "repo": "beta/beta-tool",
                "title": "备选观察",
                "why": "冷门但实用",
                "value": "补充技能面",
                "how": "收藏即可",
            },
            {
                "repo": "owner/alpha",
                "title": "再来一个",
                "why": "社区活跃",
                "value": "提问有回应",
                "how": "加 star 关注",
            },
        ],
    }


class ParseCountTest(unittest.TestCase):
    def test_parses_comma_numbers(self):
        self.assertEqual(parse_count("1,234"), 1234)

    def test_returns_none_for_empty_or_non_numeric(self):
        self.assertIsNone(parse_count(""))
        self.assertIsNone(parse_count(None))
        self.assertIsNone(parse_count("stars"))


class ParseTrendingHtmlTest(unittest.TestCase):
    def test_parses_repos_with_fields(self):
        repos = parse_trending_html(FIXTURE_HTML, limit=15)
        self.assertEqual(len(repos), 2)

        alpha = repos[0]
        self.assertEqual(alpha.rank, 1)
        self.assertEqual(alpha.full_name, "owner/alpha")
        self.assertEqual(alpha.url, "https://github.com/owner/alpha")
        self.assertEqual(alpha.description, "Alpha does things well")
        self.assertEqual(alpha.language, "Python")
        self.assertEqual(alpha.stars, 1234)
        self.assertEqual(alpha.forks, 56)
        self.assertEqual(alpha.stars_today, 98)
        self.assertEqual(alpha.topics, ["ai", "tools"])

        beta = repos[1]
        self.assertEqual(beta.full_name, "beta/beta-tool")
        self.assertEqual(beta.stars, 999)
        self.assertIsNone(beta.stars_today)
        self.assertEqual(beta.language, "")

    def test_respects_limit(self):
        repos = parse_trending_html(FIXTURE_HTML, limit=1)
        self.assertEqual([repo.full_name for repo in repos], ["owner/alpha"])

    def test_skips_non_repo_rows(self):
        repos = parse_trending_html(FIXTURE_HTML, limit=15)
        self.assertNotIn("topics/not-a-repo", [r.full_name for r in repos])


class ValidatePayloadTest(unittest.TestCase):
    def test_accepts_valid_payload(self):
        result = validate_payload(make_payload(), make_repos())
        self.assertEqual(set(result["projects"]), {"owner/alpha", "beta/beta-tool"})
        self.assertEqual(len(result["highlights"]), 3)

    def test_rejects_unknown_repo(self):
        payload = make_payload()
        payload["repos"][1]["repo"] = "ghost/unknown"
        with self.assertRaisesRegex(ValueError, "unknown repo"):
            validate_payload(payload, make_repos())

    def test_rejects_incomplete_coverage(self):
        payload = make_payload()
        payload["repos"] = payload["repos"][:1]
        with self.assertRaisesRegex(ValueError, "not fully covered"):
            validate_payload(payload, make_repos())

    def test_rejects_duplicate_repo(self):
        payload = make_payload()
        payload["repos"][1] = dict(payload["repos"][0])
        with self.assertRaisesRegex(ValueError, "duplicate repo"):
            validate_payload(payload, make_repos())

    def test_rejects_bad_highlight_count(self):
        payload = make_payload()
        payload["highlights"] = payload["highlights"][:2]
        with self.assertRaisesRegex(ValueError, "highlights must contain"):
            validate_payload(payload, make_repos())

    def test_rejects_repo_without_how_to_start(self):
        payload = make_payload()
        del payload["repos"][0]["how"]
        with self.assertRaisesRegex(ValueError, "what/help/how missing"):
            validate_payload(payload, make_repos())

    def test_rejects_highlight_with_unknown_repo(self):
        payload = make_payload()
        payload["highlights"][0]["repo"] = "ghost/unknown"
        with self.assertRaisesRegex(ValueError, "unknown repo"):
            validate_payload(payload, make_repos())


class ExtractJsonTest(unittest.TestCase):
    def test_parses_plain_json(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})

    def test_parses_fenced_json(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_parses_json_with_surrounding_text(self):
        self.assertEqual(extract_json('结果如下：{"a": 1} 请查收'), {"a": 1})


class BuildRecordTest(unittest.TestCase):
    def test_analyzed_mode_contains_digest(self):
        record = build_record("2026-08-31", make_repos(), validate_payload(make_payload(), make_repos()), "2026-08-31 09:20")
        self.assertEqual(record["mode"], "analyzed")
        self.assertEqual(record["intro"], "今日榜单风向：AI 工具链继续升温。")
        self.assertEqual(len(record["highlights"]), 3)
        alpha = record["repos"][0]
        self.assertEqual(alpha["what"], "一个做 X 的工具。")
        self.assertEqual(alpha["help"], "适合你练手。")
        self.assertEqual(alpha["how"], "先跑示例。")

    def test_fallback_mode_keeps_raw_board(self):
        record = build_record("2026-08-31", make_repos(), None, "2026-08-31 09:20")
        self.assertEqual(record["mode"], "fallback")
        self.assertEqual(record["highlights"], [])
        self.assertEqual(record["repos"][0]["what"], "Alpha does things well")
        self.assertEqual(record["repos"][1]["what"], "")


class BuildUserPromptTest(unittest.TestCase):
    def test_prompt_lists_every_repo(self):
        prompt = build_user_prompt(make_repos())
        self.assertIn("owner/alpha", prompt)
        self.assertIn("beta/beta-tool", prompt)
        self.assertIn("+98", prompt)


class PublisherContractTest(unittest.TestCase):
    def test_artifact_contract(self):
        self.assertEqual(
            publisher_artifacts("2026-08-31"),
            {"src/data/github-daily/2026-08-31.json"},
        )
        self.assertEqual(
            publisher_commit_message("2026-08-31"),
            "chore: add GitHub daily trending for 2026-08-31",
        )
        self.assertEqual(
            publisher_remote_artifact("2026-08-31"),
            "src/data/github-daily/2026-08-31.json",
        )

    def test_ai_daily_defaults_unchanged(self):
        publisher = Publisher("/tmp")
        self.assertEqual(
            publisher.artifacts("2026-08-31"),
            {
                "src/content/ai-daily/2026-08-31.md",
                "public/ai-daily.xml",
                "src/data/ai-trends.json",
            },
        )
        self.assertEqual(
            publisher.commit_message("2026-08-31"),
            "chore: add AI daily report for 2026-08-31",
        )
        self.assertEqual(
            publisher.remote_artifact("2026-08-31"),
            "src/content/ai-daily/2026-08-31.md",
        )


if __name__ == "__main__":
    unittest.main()
