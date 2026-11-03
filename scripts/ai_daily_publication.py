"""Verify source bytes, served application assets and the exact RSS entry together."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urljoin
import xml.etree.ElementTree as ET


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def report_title(raw: str) -> str:
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    frontmatter = re.match(r'^---\n(.*?)\n---(?:\n|$)', raw, re.S)
    match = re.search(r'^title:\s*(.+)$', frontmatter[1] if frontmatter else '', re.M)
    if not match:
        return 'AI Daily Report'
    try:
        value = json.loads(match[1])
        return value if isinstance(value, str) else match[1]
    except ValueError:
        return match[1].strip().strip("'\"")


def report_excerpt(raw: str) -> str:
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    body = raw.split('---\n', 2)[-1] if '---\n' in raw else raw
    return '\n'.join(line.rstrip() for line in re.sub(r'<[^>]+>', '', body[:500]).splitlines()).strip()


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        path = None
        if tag == 'script' and attrs.get('type') == 'module':
            path = attrs.get('src')
        elif tag == 'link' and attrs.get('rel') == 'stylesheet':
            path = attrs.get('href')
        if path and path.startswith('/assets/') and not any(part in path for part in ('..', '?', '#', '\\')):
            self.paths.add(path)


def asset_paths(html):
    parser = AssetParser()
    parser.feed(html)
    return parser.paths


def artifact_route(path: str) -> str | None:
    match = re.fullmatch(r'src/content/ai-daily/(\d{4}-\d{2}-\d{2})\.md', path)
    if match:
        return f'/ai-daily/{match[1]}'
    match = re.fullmatch(r'src/data/github-daily/(\d{4}-\d{2}-\d{2})\.json', path)
    return f'/github/{match[1]}' if match else None


def build_manifest(root: Path, dist: Path) -> dict:
    """Run after Vite, so these hashes describe the application actually deployed."""
    assets = {}
    for path in sorted(asset_paths((dist / 'index.html').read_text(encoding='utf-8'))):
        file = (dist / path.lstrip('/')).resolve()
        file.relative_to(dist.resolve())
        assets[path] = digest(file.read_bytes())
    if not assets or not any(path.endswith('.js') for path in assets):
        raise ValueError('Cannot attest a build without its entry JavaScript')
    reports = {}
    for directory, pattern in [('src/content/ai-daily', '????-??-??.md'),
                               ('src/data/github-daily', '????-??-??.json')]:
        for file in sorted((root / directory).glob(pattern)):
            relative = file.relative_to(root).as_posix()
            route = artifact_route(relative)
            if route:
                reports[relative] = {'route': route, 'sha256': digest(file.read_bytes())}
    manifest = {'schemaVersion': 1, 'reports': reports, 'assets': assets}
    (dist / 'daily-publication.json').write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def fetch_bytes(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'ai-daily-sop/2.0', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError('Publication endpoint did not return HTTP 200')
        data = response.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError('Publication response exceeds size bound')
    return data


def verify_publication(base_url: str, artifact: str, expected: bytes, *, rss_url=None, fetch=fetch_bytes) -> bool:
    try:
        route = artifact_route(artifact)
        if route is None:
            return False
        manifest = json.loads(fetch(urljoin(base_url, '/daily-publication.json')))
        if manifest.get('schemaVersion') != 1:
            return False
        record = manifest['reports'][artifact]
        if record.get('route') != route or record.get('sha256') != digest(expected):
            return False
        assets = manifest['assets']
        if not isinstance(assets, dict) or not 1 <= len(assets) <= 32:
            return False
        html = fetch(urljoin(base_url, route)).decode('utf-8')
        if set(assets) != asset_paths(html) or not any(path.endswith('.js') for path in assets):
            return False
        for path, expected_hash in assets.items():
            if digest(fetch(urljoin(base_url, path))) != expected_hash:
                return False
        if rss_url is not None:
            raw = expected.decode('utf-8')
            feed = ET.fromstring(fetch(rss_url))
            matches = [item for item in feed.findall('./channel/item')
                       if item.findtext('link') == urljoin(base_url, route)]
            if len(matches) != 1:
                return False
            if matches[0].findtext('title') != report_title(raw):
                return False
            if matches[0].findtext('description') != report_excerpt(raw):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ET.ParseError, UnicodeError):
        return False


if __name__ == '__main__':
    project = Path(__file__).resolve().parent.parent
    build_manifest(project, project / 'dist')
    print('Daily publication manifest generated from built assets and report bytes')
