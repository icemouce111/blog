import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
from threading import Thread
import unittest
from pathlib import Path

from scripts.ai_daily_publication import build_manifest, verify_publication, report_excerpt


class PublicationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dist = self.root / 'dist'
        (self.dist / 'assets').mkdir(parents=True)
        (self.dist / 'index.html').write_text('<html><script type="module" src="/assets/app.js"></script></html>')
        (self.dist / 'assets/app.js').write_text('compiled application containing the current daily data')
        self.artifact = 'src/content/ai-daily/2026-07-01.md'
        path = self.root / self.artifact
        path.parent.mkdir(parents=True)
        self.raw = '---\ntitle: "今日日报"\ndate: 2026-07-01\n---\n\n## 01 今日变化\n\n1. 新内容。[来源](https://example.org/news)\n'
        path.write_text(self.raw)
        build_manifest(self.root, self.dist)
        self.responses = {
            '/daily-publication.json': (self.dist / 'daily-publication.json').read_bytes(),
            '/ai-daily/2026-07-01': (self.dist / 'index.html').read_bytes(),
            '/assets/app.js': (self.dist / 'assets/app.js').read_bytes(),
            '/ai-daily.xml': ('<rss><channel><item><title>今日日报</title>'
                             '<link>https://blog.example/ai-daily/2026-07-01</link>'
                             '<description><![CDATA[' + report_excerpt(self.raw) + ']]></description>'
                             '</item></channel></rss>').encode(),
        }

    def verify(self, *, rss=True, raw=None, artifact=None):
        return verify_publication('https://blog.example', artifact or self.artifact,
                                  (raw or self.raw).encode(),
                                  rss_url='https://blog.example/ai-daily.xml' if rss else None,
                                  fetch=lambda url: self.responses[url.removeprefix('https://blog.example')])

    def test_accepts_exact_report_served_by_the_matching_build_and_rss_item(self):
        self.assertTrue(self.verify())

    def test_date_mentioned_in_another_rss_item_does_not_prove_publication(self):
        self.responses['/ai-daily.xml'] = b'<rss><channel><item><title>old</title><link>https://blog.example/ai-daily/2026-06-30</link><description>2026-07-01</description></item></channel></rss>'
        self.assertFalse(self.verify())

    def test_same_date_and_title_with_old_content_is_rejected(self):
        self.assertFalse(self.verify(raw=self.raw.replace('新内容', '更正后的新内容')))

    def test_new_manifest_with_cached_old_application_is_rejected(self):
        self.responses['/assets/app.js'] = b'cached old bundle'
        self.assertFalse(self.verify())

    def test_spa_200_with_old_asset_urls_is_rejected(self):
        self.responses['/ai-daily/2026-07-01'] = b'<script type="module" src="/assets/old.js"></script>'
        self.assertFalse(self.verify())

    def test_github_board_requires_a_matching_online_build_even_without_rss(self):
        path = self.root / 'src/data/github-daily/2026-07-01.json'
        path.parent.mkdir(parents=True)
        raw = json.dumps({'date': '2026-07-01', 'repos': []})
        path.write_text(raw)
        build_manifest(self.root, self.dist)
        self.responses['/daily-publication.json'] = (self.dist / 'daily-publication.json').read_bytes()
        self.responses['/github/2026-07-01'] = self.responses['/ai-daily/2026-07-01']
        self.assertTrue(self.verify(rss=False, raw=raw, artifact='src/data/github-daily/2026-07-01.json'))
        del self.responses['/daily-publication.json']
        self.assertFalse(self.verify(rss=False, raw=raw, artifact='src/data/github-daily/2026-07-01.json'))

    def test_real_http_path_validates_current_bytes_and_rejects_a_stale_spa(self):
        responses = self.responses
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200 if self.path in responses else 404)
                self.end_headers()
                self.wfile.write(responses.get(self.path, b'not found'))
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        responses['/ai-daily.xml'] = responses['/ai-daily.xml'].replace(b'https://blog.example', base.encode())
        try:
            self.assertTrue(verify_publication(base, self.artifact, self.raw.encode(), rss_url=base + '/ai-daily.xml'))
            responses['/assets/app.js'] = b'old application'
            self.assertFalse(verify_publication(base, self.artifact, self.raw.encode(), rss_url=base + '/ai-daily.xml'))
        finally:
            server.shutdown()
            worker.join()
            server.server_close()

    def test_line_endings_do_not_change_rss_title_or_excerpt_matching(self):
        raw = self.raw.replace('\n', '\r\n')
        (self.root / self.artifact).write_bytes(raw.encode())
        build_manifest(self.root, self.dist)
        self.responses['/daily-publication.json'] = (self.dist / 'daily-publication.json').read_bytes()
        self.assertTrue(self.verify(raw=raw))
