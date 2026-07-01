import unittest
from datetime import date

from scripts.ai_daily_sources import (
    AnthropicNewsSource,
    CallableSource,
    LinuxDoSource,
    OpenAINewsSource,
    RedditSource,
    SourceContext,
    SourceRegistry,
    SourceResult,
    SourceStatus,
    SourceTier,
    XiaohongshuSource,
    XSource,
)


class FakeTransport:
    def __init__(self):
        self.text = {}
        self.json = {}
        self.posts = {}
        self.calls = []

    def get_text(self, url, *, headers=None, timeout=20):
        self.calls.append(("text", url, headers))
        value = self.text[url]
        if isinstance(value, Exception):
            raise value
        return value

    def get_json(self, url, *, headers=None, timeout=20):
        self.calls.append(("json", url, headers))
        value = self.json[url]
        if isinstance(value, Exception):
            raise value
        return value

    def post_json(self, url, payload, *, headers=None, timeout=20):
        self.calls.append(("post", url, payload))
        value = self.posts[url]
        if isinstance(value, Exception):
            raise value
        return value


def context(**env):
    return SourceContext(
        target_date=date(2026, 7, 1),
        limit=10,
        env=env,
    )


class OfficialSourceTest(unittest.TestCase):
    def test_openai_rss_produces_official_items(self):
        transport = FakeTransport()
        transport.text["https://openai.com/news/rss.xml"] = """<?xml version="1.0"?>
        <rss><channel><item>
          <title>New OpenAI release</title>
          <link>https://openai.com/index/new-release/</link>
          <description>Release details.</description>
          <pubDate>Tue, 30 Jun 2026 12:00:00 GMT</pubDate>
        </item></channel></rss>"""

        result = OpenAINewsSource(transport).fetch(context())

        self.assertEqual(result.status, SourceStatus.ACTIVE)
        self.assertEqual(result.items[0].source, "OpenAI")
        self.assertEqual(result.items[0].source_tier, SourceTier.OFFICIAL)
        self.assertEqual(result.items[0].published_at, "2026-06-30T12:00:00+00:00")

    def test_anthropic_uses_newsroom_links_and_sitemap_dates(self):
        transport = FakeTransport()
        transport.text["https://www.anthropic.com/sitemap.xml"] = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.anthropic.com/news/sonnet-5</loc>
          <lastmod>2026-06-30</lastmod></url>
        </urlset>"""
        transport.text["https://www.anthropic.com/news"] = """
        <html><body><a href="/news/sonnet-5">Introducing Claude Sonnet 5</a></body></html>
        """

        result = AnthropicNewsSource(transport).fetch(context())

        self.assertEqual(result.status, SourceStatus.ACTIVE)
        self.assertEqual(result.items[0].title, "Introducing Claude Sonnet 5")
        self.assertEqual(result.items[0].published_at, "2026-06-30")
        self.assertEqual(result.items[0].source_tier, SourceTier.OFFICIAL)


class CommunitySourceTest(unittest.TestCase):
    def test_linuxdo_parses_discourse_rss(self):
        transport = FakeTransport()
        transport.text["https://linux.do/latest.rss"] = """<?xml version="1.0"?>
        <rss><channel><item>
          <title>AI 工具讨论</title>
          <link>https://linux.do/t/topic/123</link>
          <description><![CDATA[<p>社区讨论内容</p>]]></description>
          <pubDate>Tue, 30 Jun 2026 10:00:00 GMT</pubDate>
        </item></channel></rss>"""

        result = LinuxDoSource(transport).fetch(context())

        self.assertEqual(result.status, SourceStatus.ACTIVE)
        self.assertEqual(result.items[0].source, "Linux.do")
        self.assertEqual(result.items[0].source_tier, SourceTier.COMMUNITY)

    def test_reddit_uses_public_json_before_browser_fallback(self):
        transport = FakeTransport()
        url = "https://www.reddit.com/r/MachineLearning/hot.json?limit=10"
        transport.json[url] = {
            "data": {
                "children": [{
                    "data": {
                        "id": "abc",
                        "title": "A useful AI thread",
                        "permalink": "/r/MachineLearning/comments/abc/thread/",
                        "selftext": "Details",
                        "author": "researcher",
                        "created_utc": 1782813600,
                        "score": 100,
                        "num_comments": 20,
                    }
                }]
            }
        }
        fallback_calls = []

        result = RedditSource(
            transport,
            subreddits=("MachineLearning",),
            fallback=lambda: fallback_calls.append(True) or [],
        ).fetch(context())

        self.assertEqual(result.status, SourceStatus.ACTIVE)
        self.assertEqual(result.items[0].engagement["score"], 100)
        self.assertEqual(fallback_calls, [])

    def test_x_prefers_official_api_and_degrades_to_browser(self):
        transport = FakeTransport()
        api_url = XSource.recent_search_url("AI OR LLM", 10)
        transport.json[api_url] = {
            "data": [{
                "id": "42",
                "text": "AI release details",
                "author_id": "u1",
                "created_at": "2026-06-30T09:00:00.000Z",
                "public_metrics": {
                    "like_count": 50,
                    "retweet_count": 5,
                    "reply_count": 3,
                    "quote_count": 1,
                },
            }],
            "includes": {"users": [{"id": "u1", "username": "builder"}]},
        }

        official = XSource(transport, query="AI OR LLM").fetch(
            context(X_BEARER_TOKEN="secret")
        )
        degraded = XSource(
            FakeTransport(),
            fallback=lambda: [{
                "text": "browser item",
                "url": "https://x.com/example/status/9",
                "author": "example",
            }],
        ).fetch(context())

        self.assertEqual(official.status, SourceStatus.ACTIVE)
        self.assertEqual(official.items[0].url, "https://x.com/builder/status/42")
        self.assertEqual(degraded.status, SourceStatus.DEGRADED)
        self.assertEqual(degraded.items[0].metadata["retrieval"], "browser-fallback")

    def test_xiaohongshu_prefers_logged_in_mcp_and_degrades_to_browser(self):
        transport = FakeTransport()
        base = "http://127.0.0.1:18060"
        transport.json[f"{base}/api/v1/login/status"] = {
            "data": {"is_logged_in": True}
        }
        transport.posts[f"{base}/api/v1/feeds/search"] = {
            "data": {
                "feeds": [{
                    "id": "note1",
                    "xsecToken": "token",
                    "noteCard": {
                        "displayTitle": "AI 笔记",
                        "desc": "体验记录",
                        "time": 1782813600000,
                        "user": {"nickname": "作者"},
                        "interactInfo": {
                            "likedCount": "1.2万",
                            "commentCount": "20",
                            "collectedCount": "300",
                        },
                    },
                }]
            }
        }

        official = XiaohongshuSource(transport).fetch(
            context(XIAOHONGSHU_API_BASE=base)
        )
        degraded = XiaohongshuSource(
            FakeTransport(),
            fallback=lambda: [{
                "title": "浏览器笔记",
                "url": "https://www.xiaohongshu.com/explore/browser",
            }],
        ).fetch(context())

        self.assertEqual(official.status, SourceStatus.ACTIVE)
        self.assertEqual(official.items[0].engagement["likes"], 12000)
        self.assertEqual(degraded.status, SourceStatus.DEGRADED)


class RegistryTest(unittest.TestCase):
    def test_callable_source_preserves_legacy_engagement_fields(self):
        result = CallableSource(
            "Legacy",
            SourceTier.COMMUNITY,
            lambda: [{
                "title": "Legacy item",
                "url": "https://example.com/legacy",
                "score": 20,
                "comments": 4,
            }],
        ).fetch(context())

        self.assertEqual(
            result.items[0].engagement,
            {"score": 20, "comments": 4},
        )

    def test_registry_deduplicates_urls_and_preserves_source_status(self):
        duplicate_url = "https://example.com/item?utm_source=test"

        class First:
            name = "First"

            def fetch(self, _context):
                return SourceResult.from_dicts(
                    "First",
                    SourceTier.AGGREGATOR,
                    [{"title": "First title", "url": duplicate_url}],
                )

        class Second:
            name = "Second"

            def fetch(self, _context):
                return SourceResult.from_dicts(
                    "Second",
                    SourceTier.COMMUNITY,
                    [{"title": "Second title", "url": "https://example.com/item"}],
                )

        results = SourceRegistry([First(), Second()]).fetch_all(context())

        self.assertEqual(results["First"].status, SourceStatus.ACTIVE)
        self.assertEqual(results["Second"].status, SourceStatus.ACTIVE)
        self.assertEqual(sum(len(result.items) for result in results.values()), 1)


if __name__ == "__main__":
    unittest.main()
