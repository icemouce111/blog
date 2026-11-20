"""Read publication history from the existing, versioned daily Markdown files."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo


URLS = re.compile(r"https?://[^\s<>\])]+")
NUMBERED = re.compile(r"(?ms)^\d+\.\s+.*?(?=^\d+\.\s+|^##\s+|\Z)")
_HISTORY_START = r'(?:\d+\.[ \t]+|(?:[-*+][ \t]+)?\*\*[^*\n]+\*\*)'
HISTORY_ITEMS = re.compile(r'(?ms)^' + _HISTORY_START + r'.*?(?=^' + _HISTORY_START + r'|^##\s+|\Z)')


def shanghai_day(value) -> date | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(ZoneInfo('Asia/Shanghai'))
        return parsed.date()
    except ValueError:
        return None


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_')]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix('www.'),
                       parts.path.rstrip('/'), urlencode(query), ''))


def event_title(title: str) -> str:
    return re.sub(r'[^\w\u4e00-\u9fff]', '', unicodedata.normalize('NFKC', title).casefold())


def material_hash(item) -> str:
    # Popularity counters and retrieval time are not editorial changes.
    text = ' '.join(f'{item.title}\n{item.summary}'.split())
    return hashlib.sha256(text.encode()).hexdigest()


def read_history(directory: Path, target: date) -> list[dict]:
    history = []
    for path in sorted(directory.glob('????-??-??.md'), reverse=True):
        try:
            published = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if published >= target:
            continue  # Same-day reruns and historical backfills must not see the future.
        raw = path.read_text(encoding='utf-8')
        body = raw.split('---\n', 2)[-1].split('\n---\n\n*本情报', 1)[0].strip()
        receipt = re.search(r'^evidence:\s*(\{[^\n]+\})\s*$', raw, re.M)
        try:
            record = json.loads(receipt[1]) if receipt else {}
            start = re.search(r'^##\s+\d{2}\b', body, re.M)
            editorial = body[start.start():].strip() if start else body
            trusted_receipt = record.get('report_hash') == hashlib.sha256(editorial.encode()).hexdigest()
            saved = record.get('items', []) if trusted_receipt else []
        except (ValueError, TypeError, AttributeError):
            saved = []
        # Existing reports also use standalone bold titles and source-archive
        # bullets. Keep their following paragraphs and URLs, including mixed styles.
        blocks = HISTORY_ITEMS.findall(body)
        if not isinstance(saved, list) or len(saved) != len(blocks) or any(not isinstance(entry, dict) for entry in saved):
            saved = []
        for index, block in enumerate(blocks):
            urls = sorted({canonical_url(url) for url in URLS.findall(block)})
            if not urls:
                continue
            heading = re.search(r'\*\*(.+?)\*\*', block)
            title = heading[1] if heading else block.splitlines()[0]
            sources = saved[index].get('sources', []) if index < len(saved) and isinstance(saved[index], dict) else []
            sources = [source for source in sources if isinstance(source, dict) and isinstance(source.get('url'), str)] if isinstance(sources, list) else []
            citations = saved[index].get('citations', []) if index < len(saved) else []
            quotes = [citation['quote'] for citation in citations if isinstance(citation, dict) and isinstance(citation.get('quote'), str)] if isinstance(citations, list) else []
            history.append({'id': f'{path.stem}:{index + 1}', 'date': path.stem,
                            'title': title, 'event_key': event_title(title),
                            'urls': urls, 'text': block[:1800], 'quotes': quotes, 'sources': sources})
    return history


def prepare_history(items, history: list[dict], target: date):
    """Drop repeats; retain changed, dated updates for explicit incremental review."""
    output = []
    for item in items:
        basis = item.metadata.get('date_basis', 'published')
        if basis in {'snapshot', 'deadline'} or item.metadata.get('signal_type') in {'trend', 'opportunity'}:
            output.append(item)
            continue
        url = canonical_url(item.url)
        matches = [old for old in history if url in old['urls'] or event_title(item.title) == old['event_key']]
        if not matches:
            output.append(item)
            continue
        updated_day = shanghai_day(item.metadata.get('updated_at'))
        previous_hashes = {source['content_hash'] for old in matches for source in old.get('sources', [])
                           if canonical_url(source.get('url', '')) == url
                           and isinstance(source.get('content_hash'), str)
                           and re.fullmatch(r'[a-f0-9]{64}', source['content_hash'])}
        # Legacy reports without material hashes cannot prove an update. A new URL
        # for the same event can proceed to the semantic check, never an old URL.
        same_url = any(url in old['urls'] for old in matches)
        changed_update = (previous_hashes and material_hash(item) not in previous_hashes
                          and updated_day is not None and updated_day <= target
                          and updated_day.isoformat() > max(old['date'] for old in matches))
        if same_url and not changed_update:
            continue
        item.metadata['previous_reports'] = [old['id'] for old in matches]
        if changed_update:
            item.metadata['freshness_at'] = updated_day.isoformat()
        output.append(item)
    return output
