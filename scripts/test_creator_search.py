import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.creator_search import load_agent_searches, read_rss, search_leads


class CreatorSearchTest(unittest.TestCase):
    def test_native_search_preserves_material_and_avoids_repeating_successful_queries(self):
        result = search_leads('AI创作者', 1, agent_results={'AI创作者': {'items': [
            {'title':'创作计划','url':'https://example.org/creator','summary':'AI创作者招募。'}]}},
            accept=lambda item:'招募' in item['summary'],
            fetch=lambda *_:self.fail('A relevant native result must not be searched again'))
        self.assertEqual(result.items[0]['engine'], 'codex-web')
        self.assertEqual(result.items[0]['summary'], 'AI创作者招募。')

    def test_irrelevant_native_results_try_the_public_fallback(self):
        result = search_leads('AI创作者', 1, agent_results={'AI创作者': {'items': [
            {'title':'游泳网站','url':'https://swimming.example/events','summary':'Open water'}]}},
            accept=lambda item:'招募' in item['summary'],
            fetch=lambda *_:[{'title':'创作计划','url':'https://example.org/creator','summary':'AI创作者招募。'}])
        self.assertEqual([x['state'] for x in result.attempts], ['irrelevant','relevant'])
        self.assertEqual(result.items[0]['engine'],'bing-rss')

    def test_blocked_and_empty_searches_remain_distinct(self):
        def unavailable(*_):raise TimeoutError()
        blocked = search_leads('AI创作者',1,fetch=unavailable)
        empty = search_leads('AI创作者',1,fetch=lambda *_:[])
        self.assertEqual(blocked.attempts[0]['state'],'unavailable')
        self.assertEqual(empty.attempts[0]['state'],'empty')

    def test_handoff_rejects_stale_dates_unplanned_queries_duplicates_and_bad_material(self):
        good={'date':'2026-11-17','queries':[{'query':'AI创作者','items':[
            {'title':'创作计划','url':'https://example.org/program','summary':'知识共创招募'}]}]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'search.json'
            path.write_text(json.dumps(good))
            self.assertIn('AI创作者',load_agent_searches(path,'2026-11-17',{'AI创作者'}))
            bad_cases=[dict(good,date='2026-11-16'),dict(good,queries=[{'query':'其他查询','items':[]}]),
                       dict(good,queries=good['queries']*2),dict(good,queries=[{'query':'AI创作者','items':[{'url':'https://example.org'}]}])]
            for bad in bad_cases:
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):load_agent_searches(path,'2026-11-17',{'AI创作者'})

    def test_rss_fallback_retains_summary_and_date_as_unverified_search_hints(self):
        import io
        raw=b'<rss><channel><item><title>AI creator</title><link>https://example.org/post</link><description>Creator program</description><pubDate>2026-11-17</pubDate></item></channel></rss>'
        with patch('scripts.creator_search.urllib.request.urlopen',return_value=io.BytesIO(raw)):
            item=read_rss('AI creator',1)[0]
        self.assertEqual(item['summary'],'Creator program')
        self.assertEqual(item['dateHint'],'2026-11-17')
        self.assertNotIn('publishedAt',item)


if __name__ == '__main__':unittest.main()
