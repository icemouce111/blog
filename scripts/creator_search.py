"""Codex web-search handoff, with public RSS as a bounded fallback."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


@dataclass
class SearchOutcome:
    items: list[dict]
    attempts: list[dict]


def load_agent_searches(path, reference, allowed_queries):
    if not path:
        return {}
    with Path(path).open('rb') as stream:
        raw = stream.read(500_001)
    if len(raw) > 500_000:
        raise ValueError('Creator search handoff exceeds size limit')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('date') != str(reference) or not isinstance(data.get('queries'), list):
        raise ValueError('Creator search handoff has a stale date or invalid queries')
    if len(data['queries']) > len(allowed_queries):
        raise ValueError('Creator search handoff exceeds query budget')
    output = {}
    for entry in data['queries']:
        if not isinstance(entry, dict):
            raise ValueError('Creator search query must be an object')
        query = entry.get('query')
        items = entry.get('items')
        if not isinstance(query, str) or query not in allowed_queries or query in output or not isinstance(items, list) or len(items) > 10:
            raise ValueError('Creator search handoff contains an unknown/duplicate query or invalid items')
        if entry.get('error') and items:
            raise ValueError('Failed creator search cannot contain successful results')
        for item in items:
            if not isinstance(item, dict) or any(not isinstance(item.get(key), str) for key in ('title', 'url', 'summary')):
                raise ValueError('Creator search item needs title, URL and summary')
            if len(item['title']) > 500 or len(item['url']) > 8192 or len(item['summary']) > 2000:
                raise ValueError('Creator search item exceeds text limit')
        output[query] = entry
    return output


def read_rss(query, timeout):
    url = 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': query, 'format': 'rss'})
    request = urllib.request.Request(url, headers={'User-Agent': 'creator-opportunity-radar/2.0'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(500_001)
    if len(data) > 500_000:
        raise ValueError('Creator search response exceeds size limit')
    root = ET.fromstring(data)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Creator search returned an unrecognized response')
    return [{'title': node.findtext('title') or '', 'url': node.findtext('link') or '',
             'summary': node.findtext('description') or '', 'dateHint': node.findtext('pubDate') or ''}
            for node in root.findall('./channel/item')[:10]]


def search_leads(query, timeout, *, accept=lambda item: True, agent_results=None, fetch=None):
    attempts = []
    imported = (agent_results or {}).get(query)
    if imported is not None:
        items = [dict(item, engine='codex-web') for item in imported['items']]
        accepted = [item for item in items if accept(item)]
        attempts.append({'engine': 'codex-web', 'rawResults': len(items), 'accepted': len(accepted),
                         'state': 'unavailable' if imported.get('error') else 'relevant' if accepted else 'irrelevant' if items else 'empty'})
        if accepted:
            return SearchOutcome(accepted, attempts)
    try:
        items = [dict(item, engine='bing-rss') for item in (fetch or read_rss)(query, timeout)]
        accepted = [item for item in items if accept(item)]
        attempts.append({'engine': 'bing-rss', 'rawResults': len(items), 'accepted': len(accepted),
                         'state': 'relevant' if accepted else 'irrelevant' if items else 'empty'})
        return SearchOutcome(accepted, attempts)
    except (OSError, ValueError, ET.ParseError) as error:
        attempts.append({'engine': 'bing-rss', 'rawResults': 0, 'accepted': 0,
                         'state': 'unavailable', 'error': type(error).__name__})
        return SearchOutcome([], attempts)
