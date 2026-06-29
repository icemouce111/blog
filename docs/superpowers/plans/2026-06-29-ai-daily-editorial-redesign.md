# AI Daily Editorial Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the AI Daily archive and issue pages as a responsive Chinese editorial briefing, add sourced week/month/year global AI application trends, normalize the three raw historical issues, and make future fallback reports use the same parseable structure.

**Architecture:** Keep Markdown as the source of truth for daily issues and use a validated JSON snapshot for cross-issue trends. Extract Markdown-to-view-model logic into a pure TypeScript parser, then render focused React components for masthead, lead story, issue stream, trend rail, sidebar, and mobile summary. Preserve existing generator changes, add an isolated trend-refresh helper with source-whitelist validation, and mechanically migrate the three raw historical files without inventing editorial analysis.

**Tech Stack:** React 19, React Router 7, TypeScript 6, Vite 8, Tailwind CSS 4, React Markdown, Node 26 built-in test runner, Python unittest.

---

## File map

- Create `src/lib/ai-daily-parser.ts`: pure parser and derived issue metrics.
- Create `tests/ai-daily-parser.test.ts`: parser regression tests for editorial, archive, and malformed content.
- Create `src/lib/ai-trends.ts`: validate and expose week/month/year trend snapshots.
- Create `tests/ai-trends.test.ts`: trend schema and fallback tests.
- Modify `src/lib/ai-daily.ts`: load Markdown and expose parsed issue models plus adjacent issues.
- Create `src/components/ai-daily/AiDailyMasthead.tsx`: shared editorial masthead.
- Create `src/components/ai-daily/AiDailyIssueList.tsx`: latest issue and compact archive rows.
- Create `src/components/ai-daily/AiDailyContent.tsx`: lead story and section rendering.
- Create `src/components/ai-daily/AiDailyNavigation.tsx`: desktop sidebar and mobile chapter navigation.
- Create `src/components/ai-daily/AiTrendInsights.tsx`: accessible week/month/year trend switcher and source disclosure.
- Create `src/components/ai-daily/ai-daily.css`: scoped editorial visual system and responsive rules.
- Modify `src/pages/AiDailyPage.tsx`: archive landing page.
- Modify `src/pages/AiDailyPostPage.tsx`: responsive issue page.
- Modify `src/content/ai-daily/2026-06-23.md`: normalize raw summary to signal archive.
- Modify `src/content/ai-daily/2026-06-25.md`: normalize source dump to signal archive.
- Modify `src/content/ai-daily/2026-06-26.md`: normalize source dump to signal archive.
- Create `src/data/ai-trends.json`: sourced initial global AI application trend snapshot.
- Create `scripts/ai_trends.py`: archive aggregation, cadence, thresholds, prompts, and source-whitelist validation.
- Create `scripts/test_ai_trends.py`: trend refresh regression tests.
- Modify `scripts/generate-ai-daily.py`: make fallback output a numbered signal archive while preserving existing unrelated edits.
- Create `scripts/test_generate_ai_daily.py`: fallback-format regression test.
- Modify `public/ai-daily.xml`: regenerate RSS from all Markdown issues after migration.
- Modify `package.json`: add deterministic TypeScript and Python test scripts.

### Task 1: Add the pure AI Daily parser with tests

**Files:**
- Create: `tests/ai-daily-parser.test.ts`
- Create: `src/lib/ai-daily-parser.ts`
- Modify: `package.json`

- [ ] **Step 1: Add the failing parser tests**

```ts
import assert from 'node:assert/strict'
import test from 'node:test'
import { parseAiDailyContent } from './ai-daily-parser.ts'

test('parses numbered editorial sections and derives a lead story', () => {
  const result = parseAiDailyContent(`
# AI 日报

## 01 📌 今日头条

1. **模型推理进入新阶段** **[高置信度]**
   这是影响判断。
   https://example.com/lead

2. **第二条新闻**
   第二条摘要。

## 02 🔥 热门项目

1. **项目 A**
   https://example.com/project

*本日报由自动化系统生成*
`)

  assert.equal(result.sections.length, 2)
  assert.equal(result.sections[0].number, '01')
  assert.equal(result.leadStory?.title, '模型推理进入新阶段')
  assert.equal(result.leadStory?.confidence, '高置信度')
  assert.equal(result.leadStory?.sourceUrl, 'https://example.com/lead')
  assert.equal(result.storyCount, 3)
  assert.equal(result.sourceCount, 2)
  assert.equal(result.isSignalArchive, false)
  assert.match(result.sections[0].markdown, /第二条新闻/)
  assert.doesNotMatch(result.sections[0].markdown, /模型推理进入新阶段/)
})

test('recognizes a numbered signal archive without inventing an editorial edition', () => {
  const result = parseAiDailyContent(`
## 01 📡 原始信号归档

### Hacker News
- **A raw signal** [链接](https://example.com/raw)
`)

  assert.equal(result.isSignalArchive, true)
  assert.equal(result.sections[0].title, '原始信号归档')
  assert.equal(result.leadStory?.title, 'A raw signal')
})

test('falls back to the original markdown when numbered sections are absent', () => {
  const result = parseAiDailyContent('## Notes\\n\\nUnstructured content')

  assert.equal(result.sections.length, 0)
  assert.equal(result.fallbackMarkdown, '## Notes\\n\\nUnstructured content')
})

test('rejects template and non-date slugs', () => {
  assert.equal(isAiDailySlug('2026-06-28'), true)
  assert.equal(isAiDailySlug('TEMPLATE'), false)
})
```

- [ ] **Step 2: Add test scripts and verify RED**

Add to `package.json`:

```json
"test": "npm run test:ts && npm run test:py",
"test:ts": "node --test --experimental-strip-types tests/*.test.ts",
"test:py": "python3 -m unittest scripts/test_generate_ai_daily.py scripts/test_ai_trends.py"
```

Run:

```bash
npm run test:ts
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `ai-daily-parser.ts`.

- [ ] **Step 3: Implement the pure parser**

Create `src/lib/ai-daily-parser.ts` with:

```ts
export interface AiDailySection {
  number: string
  title: string
  id: string
  markdown: string
}

export interface AiDailyLeadStory {
  title: string
  summaryMarkdown: string
  confidence: string
  sourceUrl: string
}

export interface ParsedAiDailyContent {
  sections: AiDailySection[]
  leadStory: AiDailyLeadStory | null
  storyCount: number
  sourceCount: number
  readingMinutes: number
  isSignalArchive: boolean
  footer: string
  fallbackMarkdown: string
}

export function isAiDailySlug(slug: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(slug)
}

function createSectionId(number: string, title: string) {
  return `${number}-${title}`
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\u4e00-\u9fff-]/g, '')
}

function findFirstListItem(markdown: string) {
  const match = markdown.match(
    /(^|\n)((?:\d+\.\s+|-\s+)[\s\S]*?)(?=\n(?:\d+\.\s+|-\s+|###\s+)|$)/
  )
  if (!match) return null
  return { raw: match[2].trim(), start: match.index! + match[1].length }
}

function parseLeadStory(raw: string): AiDailyLeadStory {
  const title = raw.match(/\*\*(.+?)\*\*/)?.[1]?.trim() || raw.split('\n')[0].replace(/^(?:\d+\.|-)\s+/, '')
  const confidence = raw.match(/\*\*\[([^\]]+)\]\*\*|\[([^\]]*置信度)\]/)?.slice(1).find(Boolean) || ''
  const sourceUrl = raw.match(/https?:\/\/[^\s)]+/)?.[0] || ''
  const summaryMarkdown = raw
    .replace(/^(?:\d+\.|-)\s+/, '')
    .replace(/\*\*(.+?)\*\*/, '')
    .replace(/\*\*\[[^\]]+\]\*\*|\[[^\]]*置信度\]/g, '')
    .replace(/https?:\/\/[^\s)]+/g, '')
    .trim()
  return { title, summaryMarkdown, confidence, sourceUrl }
}

export function parseAiDailyContent(content: string): ParsedAiDailyContent {
  const sectionPattern = /^##\s+(\d{2})\s+(.+)$/gm
  const matches = [...content.matchAll(sectionPattern)]
  const sections = matches.map((match, index) => {
    const nextHeading = content.indexOf('\n## ', match.index! + match[0].length)
    const nextNumbered = matches[index + 1]?.index ?? content.length
    const end = nextHeading >= 0 ? Math.min(nextHeading, nextNumbered) : nextNumbered
    return {
      number: match[1],
      title: match[2].replace(/^[^\p{L}\p{N}]+/u, '').trim(),
      id: createSectionId(match[1], match[2]),
      markdown: content.slice(match.index! + match[0].length, end).trim(),
    }
  })
  const firstItem = sections[0] ? findFirstListItem(sections[0].markdown) : null
  const leadStory = firstItem ? parseLeadStory(firstItem.raw) : null
  if (sections[0] && firstItem) {
    sections[0].markdown = (
      sections[0].markdown.slice(0, firstItem.start) +
      sections[0].markdown.slice(firstItem.start + firstItem.raw.length)
    ).trim()
  }
  const urls = content.match(/https?:\/\/[^\s)]+/g) || []
  const storyCount = sections.reduce(
    (total, section) => total + (section.markdown.match(/^(?:\d+\.|-\s+)/gm)?.length || 0),
    leadStory ? 1 : 0
  )
  const readable = content.replace(/[#>*_`|:[\]()!-]/g, ' ')
  const units = (readable.match(/[\u4e00-\u9fff]/g)?.length || 0) +
    (readable.match(/[A-Za-z0-9]+/g)?.length || 0)
  const footer = content.match(/^\*本日报[\s\S]*?\*$/m)?.[0] || ''
  return {
    sections,
    leadStory,
    storyCount,
    sourceCount: new Set(urls).size,
    readingMinutes: Math.max(1, Math.ceil(units / 500)),
    isSignalArchive: sections[0]?.title.includes('原始信号归档') || false,
    footer,
    fallbackMarkdown: sections.length ? '' : content.trim(),
  }
}
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm run test:ts
npm run build
```

Expected: all parser tests PASS; TypeScript and Vite build PASS.

- [ ] **Step 5: Commit parser work**

```bash
git add package.json package-lock.json src/lib/ai-daily-parser.ts tests/ai-daily-parser.test.ts
git commit -m "feat: parse AI daily editorial content"
```

### Task 2: Expose parsed issue models from the Markdown data layer

**Files:**
- Modify: `src/lib/ai-daily.ts`
- Modify: `tests/ai-daily-parser.test.ts`

- [ ] **Step 1: Add failing metadata tests**

Extend the parser test with date-derived display behavior:

```ts
import { createIssueId, createIssueNavigation } from './ai-daily-parser.ts'

test('creates stable date issue ids and adjacent navigation', () => {
  assert.equal(createIssueId('2026-06-28'), '20260628')
  assert.deepEqual(
    createIssueNavigation(['2026-06-28', '2026-06-27', '2026-06-26'], '2026-06-27'),
    { newer: '2026-06-28', older: '2026-06-26' }
  )
})
```

- [ ] **Step 2: Verify RED**

Run `npm run test:ts`.

Expected: FAIL because `createIssueId` and `createIssueNavigation` are not exported.

- [ ] **Step 3: Implement metadata helpers and issue models**

Add to `src/lib/ai-daily-parser.ts`:

```ts
export function createIssueId(dateISO: string) {
  return dateISO.replaceAll('-', '')
}

export function createIssueNavigation(sortedSlugs: string[], currentSlug: string) {
  const index = sortedSlugs.indexOf(currentSlug)
  return {
    newer: index > 0 ? sortedSlugs[index - 1] : null,
    older: index >= 0 && index < sortedSlugs.length - 1 ? sortedSlugs[index + 1] : null,
  }
}
```

Update `src/lib/ai-daily.ts` so `AiDailyMeta` includes:

```ts
dateISO: string
issueId: string
leadTitle: string
leadSummary: string
storyCount: number
sourceCount: number
readingMinutes: number
isSignalArchive: boolean
```

Update `AiDailyPost` to include:

```ts
parsed: ParsedAiDailyContent
newerSlug: string | null
olderSlug: string | null
```

Parse each Markdown module once per accessor, discard entries whose slugs do not match `YYYY-MM-DD`, derive `dateISO` directly from frontmatter, and sort by `dateISO` instead of localized display text.

- [ ] **Step 4: Verify data layer**

Run:

```bash
npm run test:ts
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit data-layer work**

```bash
git add src/lib/ai-daily.ts src/lib/ai-daily-parser.ts tests/ai-daily-parser.test.ts
git commit -m "feat: expose AI daily issue metadata"
```

### Task 3: Add validated global AI trend snapshots

**Files:**
- Create: `tests/ai-trends.test.ts`
- Create: `src/lib/ai-trends.ts`
- Create: `src/data/ai-trends.json`

- [ ] **Step 1: Write failing trend validation tests**

```ts
import assert from 'node:assert/strict'
import test from 'node:test'
import { parseAiTrendData } from './ai-trends.ts'

test('accepts three sourced insights for every valid time window', () => {
  const data = parseAiTrendData({
    windows: [{
      window: 'week',
      rangeStart: '2026-06-23',
      rangeEnd: '2026-06-29',
      updatedAt: '2026-06-29T09:00:00+08:00',
      coverageCount: 7,
      mode: 'curated',
      insights: Array.from({ length: 3 }, (_, index) => ({
        title: `趋势 ${index + 1}`,
        summary: '有证据支持的应用趋势判断。',
        sources: [{ title: 'Source', url: `https://example.com/${index}` }],
      })),
    }],
  })
  assert.equal(data.windows[0].insights.length, 3)
})

test('drops invalid windows instead of rendering unsourced claims', () => {
  const data = parseAiTrendData({
    windows: [{ window: 'week', insights: [{ title: '无来源', summary: 'x', sources: [] }] }],
  })
  assert.equal(data.windows.length, 0)
})
```

- [ ] **Step 2: Verify RED**

Run `npm run test:ts`.

Expected: FAIL because `ai-trends.ts` does not exist.

- [ ] **Step 3: Implement the validator**

Create `src/lib/ai-trends.ts` with `TrendWindow`, `TrendInsight`, `TrendSource`, and `AiTrendData` interfaces. Implement `parseAiTrendData(input: unknown)` to accept only `week`, `month`, or `year` windows containing exactly three non-empty insights, each with at least one `http` or `https` source.

- [ ] **Step 4: Research and seed current global trends**

Use current primary or authoritative global sources. Create `src/data/ai-trends.json` with three windows and three insights per window. Record source title, direct URL, source publication date, actual coverage range, and `mode: "curated"`. Do not use search-result URLs, invented metrics, or unsourced claims.

- [ ] **Step 5: Verify and commit the seed**

Import the JSON in `ai-trends.test.ts`, pass it through `parseAiTrendData`, and assert all three windows survive with three insights each.

Run `npm run test:ts`.

Expected: PASS.

```bash
git add src/lib/ai-trends.ts tests/ai-trends.test.ts src/data/ai-trends.json
git commit -m "feat: add sourced global AI trend snapshots"
```

### Task 4: Build the shared editorial components

**Files:**
- Create: `src/components/ai-daily/AiDailyMasthead.tsx`
- Create: `src/components/ai-daily/AiDailyIssueList.tsx`
- Create: `src/components/ai-daily/AiDailyContent.tsx`
- Create: `src/components/ai-daily/AiDailyNavigation.tsx`
- Create: `src/components/ai-daily/AiTrendInsights.tsx`
- Create: `src/components/ai-daily/ai-daily.css`

- [ ] **Step 1: Create semantic shared components**

Implement:

```tsx
// AiDailyMasthead.tsx
interface AiDailyMastheadProps {
  date?: string
  issueId?: string
}

export function AiDailyMasthead({ date, issueId }: AiDailyMastheadProps) {
  return (
    <header className="ai-daily-masthead">
      <div>
        <p className="ai-daily-eyebrow">DAILY AI INTELLIGENCE</p>
        <h1>AI 日报</h1>
      </div>
      <div className="ai-daily-masthead-meta">
        {date ? <time>{date}</time> : <span>每日更新</span>}
        {issueId && <span>第 {issueId} 期</span>}
      </div>
    </header>
  )
}
```

`AiDailyIssueList` renders one featured latest issue followed by semantic archive rows. `AiDailyContent` renders the lead with a serif heading and each numbered section through `ReactMarkdown`. `AiDailyNavigation` renders both a sticky desktop `nav` and a horizontally scrollable mobile `nav`. `AiTrendInsights` uses validated trend data, defaults to `week`, exposes semantic week/month/year tabs, shows update and coverage metadata, and renders three open editorial rows.

- [ ] **Step 2: Add the scoped visual system**

In `ai-daily.css`, define:

```css
.ai-daily-shell {
  --daily-paper: oklch(0.985 0.012 82);
  --daily-ink: oklch(0.22 0.012 75);
  --daily-muted: oklch(0.5 0.02 75);
  --daily-rule: oklch(0.82 0.018 75);
  --daily-accent: oklch(0.53 0.17 35);
  color: var(--daily-ink);
}

.ai-daily-paper {
  background: var(--daily-paper);
  border-inline: 1px solid color-mix(in oklch, var(--daily-rule), transparent 30%);
}

.ai-daily-serif {
  font-family: Georgia, "Songti SC", STSong, "Noto Serif SC", serif;
}

.ai-daily-masthead {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 1rem;
  border-bottom: 3px double var(--daily-ink);
}

.ai-daily-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 15rem;
  gap: 3rem;
}

@media (max-width: 767px) {
  .ai-daily-paper { border-inline: 0; }
  .ai-daily-layout { display: block; }
  .ai-daily-desktop-nav { display: none; }
  .ai-daily-mobile-nav { display: flex; overflow-x: auto; }
}

@media (prefers-reduced-motion: reduce) {
  .ai-daily-shell { scroll-behavior: auto; }
}
```

Add scoped list, link, table, code, dark-mode, focus, and 44px touch-target rules. Do not change global blog typography.

- [ ] **Step 3: Verify component compilation**

Run:

```bash
npm run build
npx eslint src/components/ai-daily
```

Expected: PASS.

- [ ] **Step 4: Commit shared components**

```bash
git add src/components/ai-daily
git commit -m "feat: add AI daily editorial components"
```

### Task 5: Rebuild the archive and issue pages

**Files:**
- Modify: `src/pages/AiDailyPage.tsx`
- Modify: `src/pages/AiDailyPostPage.tsx`

- [ ] **Step 1: Replace the card archive page**

Use `AiDailyMasthead`, `AiDailyIssueList`, and `AiTrendInsights`. Preserve the latest issue's original frontmatter title above its derived lead-story title. Remove imports of `Card`, `Button`, `Sparkles`, and `Calendar`. Render:

```tsx
<main className="ai-daily-shell">
  <PageContainer size="wide" className="ai-daily-paper">
    <AiDailyMasthead />
    {posts.length ? (
      <div className="ai-daily-archive-layout">
        <AiDailyIssueList latest={posts[0]} archive={posts.slice(1)} />
        <AiTrendInsights />
      </div>
    ) : (
      <section className="ai-daily-empty">
        <p className="ai-daily-eyebrow">ARCHIVE</p>
        <h2 className="ai-daily-serif">编辑部正在整理今天的信号</h2>
      </section>
    )}
  </PageContainer>
</main>
```

- [ ] **Step 2: Replace the detail page**

Remove the hard-coded product-manager card grid. Render:

```tsx
<main className="ai-daily-shell">
  <PageContainer size="wide" className="ai-daily-paper">
    <Link className="ai-daily-back" to="/ai-daily">← 返回日报归档</Link>
    <AiDailyMasthead date={post.date} issueId={post.issueId} />
    <AiDailyNavigation.Mobile parsed={post.parsed} />
    <div className="ai-daily-layout">
      <article>
        <AiDailyContent post={post} />
      </article>
      <AiDailyNavigation.Desktop post={post} activeSection={activeSection} />
    </div>
  </PageContainer>
</main>
```

Observe section IDs, update the active section, and use instant scrolling when `prefers-reduced-motion` is enabled.

- [ ] **Step 3: Verify routing and compilation**

Run:

```bash
npm run build
npx eslint src/pages/AiDailyPage.tsx src/pages/AiDailyPostPage.tsx
```

Expected: PASS with no unused imports or type errors.

- [ ] **Step 4: Commit page integration**

```bash
git add src/pages/AiDailyPage.tsx src/pages/AiDailyPostPage.tsx
git commit -m "feat: redesign AI daily pages"
```

### Task 6: Normalize the three historical signal archives

**Files:**
- Modify: `src/content/ai-daily/2026-06-23.md`
- Modify: `src/content/ai-daily/2026-06-25.md`
- Modify: `src/content/ai-daily/2026-06-26.md`

- [ ] **Step 1: Convert the top-level fallback heading**

For each file, ensure the first content section is exactly:

```md
## 01 📡 原始信号归档
```

- [ ] **Step 2: Convert source headings without changing source entries**

Convert:

```md
=== Hacker News ===
```

and:

```md
## 📊 Hacker News
```

to:

```md
### Hacker News
```

Do the same for every source. Preserve all titles, metrics, descriptions, URLs, dates, slugs, and footers.

- [ ] **Step 3: Verify structural invariants**

Run:

```bash
for file in src/content/ai-daily/2026-06-{23,25,26}.md; do
  rg -n '^## 01 📡 原始信号归档$|^### ' "$file"
  ! rg -n '^## Raw Data Summary$|^## 📊 |^=== .+ ===$' "$file"
done
```

Expected: each file has one numbered archive heading, source headings are level three, and legacy headings are absent.

- [ ] **Step 4: Commit historical content**

```bash
git add src/content/ai-daily/2026-06-{23,25,26}.md
git commit -m "content: normalize historical AI daily archives"
```

### Task 7: Make future fallback and trend output match the contracts

**Files:**
- Create: `scripts/test_generate_ai_daily.py`
- Create: `scripts/ai_trends.py`
- Create: `scripts/test_ai_trends.py`
- Modify: `scripts/generate-ai-daily.py`

- [ ] **Step 1: Write the failing Python test**

```py
import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).with_name("generate-ai-daily.py")
SPEC = importlib.util.spec_from_file_location("generate_ai_daily", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class GenerateFallbackTest(unittest.TestCase):
    def test_fallback_uses_numbered_archive_and_source_subheadings(self):
        output = MODULE._generate_fallback({
            "Hacker News": [{
                "title": "A signal",
                "description": "A description",
                "url": "https://example.com/signal",
            }]
        })

        self.assertTrue(output.startswith("## 01 📡 原始信号归档"))
        self.assertIn("### Hacker News", output)
        self.assertNotIn("## 📊 Hacker News", output)
        self.assertIn("[链接](https://example.com/signal)", output)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest scripts/test_generate_ai_daily.py
```

Expected: FAIL because the current fallback begins with an unnumbered source heading.

- [ ] **Step 3: Patch only the fallback output contract**

Change `_generate_fallback` to:

```py
def _generate_fallback(sources_data):
    """Return a parseable signal archive when LLM analysis is unavailable."""
    parts = ["## 01 📡 原始信号归档", ""]
    for source_name, items in sources_data.items():
        valid_items = [
            item for item in items[:8]
            if (item.get("title") or item.get("name") or "").strip()
        ]
        if not valid_items:
            continue
        parts.append(f"### {source_name}")
        for item in valid_items:
            title = (item.get("title") or item.get("name") or "").strip()
            url = item.get("url", "")
            desc = (item.get("description") or "").strip()
            line = f"- **{title}**"
            if desc:
                line += f"：{desc[:120]}"
            if url:
                line += f" [链接]({url})"
            parts.append(line)
        parts.append("")
    if len(parts) == 2:
        parts.extend(["### 系统状态", "- 今日无有效数据。"])
    return "\n".join(parts).strip()
```

Preserve all other pre-existing uncommitted changes in `scripts/generate-ai-daily.py`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
npm run test:py
python3 -m py_compile scripts/generate-ai-daily.py
```

Expected: PASS.

- [ ] **Step 5: Record overlapping user changes**

Run `git diff -- scripts/generate-ai-daily.py` and document that the file contained pre-existing source-quality changes. Do not stage or commit the entire file without the user's confirmation; if committing, use a cached patch that contains only `_generate_fallback`.

- [ ] **Step 6: Write failing trend refresh tests**

Create `scripts/test_ai_trends.py`:

```py
import unittest
from ai_trends import should_refresh, validate_insight_sources


class AiTrendRefreshTest(unittest.TestCase):
    def test_window_thresholds_and_cadence(self):
        self.assertFalse(should_refresh("week", coverage_count=3, age_days=30))
        self.assertTrue(should_refresh("week", coverage_count=4, age_days=1))
        self.assertFalse(should_refresh("month", coverage_count=13, age_days=30))
        self.assertTrue(should_refresh("month", coverage_count=14, age_days=7))
        self.assertTrue(should_refresh("year", coverage_count=60, age_days=30))

    def test_rejects_sources_outside_archive_whitelist(self):
        allowed = {"https://example.com/known"}
        candidate = {
            "sources": [{"title": "Unknown", "url": "https://example.com/invented"}]
        }
        self.assertFalse(validate_insight_sources(candidate, allowed))
```

Run `python3 -m unittest scripts/test_ai_trends.py`.

Expected: FAIL because `scripts/ai_trends.py` does not exist.

- [ ] **Step 7: Implement isolated trend refresh**

Create `scripts/ai_trends.py` with:

```py
WINDOWS = {
    "week": {"days": 7, "minimum": 4, "cadence_days": 1},
    "month": {"days": 30, "minimum": 14, "cadence_days": 7},
    "year": {"days": 365, "minimum": 60, "cadence_days": 30},
}

def should_refresh(window, coverage_count, age_days):
    config = WINDOWS[window]
    return coverage_count >= config["minimum"] and age_days >= config["cadence_days"]

def validate_insight_sources(insight, allowed_urls):
    sources = insight.get("sources")
    return (
        isinstance(sources, list)
        and len(sources) > 0
        and all(source.get("url") in allowed_urls for source in sources)
    )
```

Add focused helpers to select Markdown files by date, extract their URLs, build a JSON-only prompt requesting exactly three application-level insights, validate all fields and sources, and atomically replace only successfully generated windows. Preserve the prior window when coverage, cadence, parsing, LLM, or source validation fails.

Modify `generate-ai-daily.py` to call the helper after saving the report and regenerating RSS. Update fallback overwrite detection to recognize `## 01 📡 原始信号归档`.

- [ ] **Step 8: Verify trend automation**

Run:

```bash
python3 -m unittest scripts/test_ai_trends.py scripts/test_generate_ai_daily.py
python3 -m py_compile scripts/ai_trends.py scripts/generate-ai-daily.py
```

Expected: PASS.

### Task 8: Regenerate RSS and run full verification

**Files:**
- Modify: `public/ai-daily.xml`

- [ ] **Step 1: Regenerate RSS without fetching or pushing**

Run:

```bash
python3 -c 'import importlib.util, pathlib; p=pathlib.Path("scripts/generate-ai-daily.py"); s=importlib.util.spec_from_file_location("daily", p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.generate_rss_feed()'
```

Expected: `public/ai-daily.xml` contains all current Markdown issues and uses their unchanged slugs.

- [ ] **Step 2: Verify RSS and all automated checks**

Run:

```bash
python3 - <<'PY'
import pathlib
import xml.etree.ElementTree as ET

root = ET.parse("public/ai-daily.xml").getroot()
items = root.findall("./channel/item")
slugs = [item.findtext("guid", "").rstrip("/").rsplit("/", 1)[-1] for item in items]
expected = sorted(
    [path.stem for path in pathlib.Path("src/content/ai-daily").glob("2026-*.md")],
    reverse=True,
)
assert slugs == expected, (slugs, expected)
print(f"RSS verified: {len(items)} issues")
PY
npm test
npm run build
npx eslint src/lib/ai-daily.ts src/lib/ai-daily-parser.ts src/lib/ai-trends.ts src/pages/AiDailyPage.tsx src/pages/AiDailyPostPage.tsx src/components/ai-daily
git diff --check
```

Expected: RSS count matches Markdown count; all tests, build, targeted lint, and whitespace checks PASS. Run full `npm run lint` separately and confirm it introduces no errors beyond the four documented baseline failures in shadcn exports and `useTheme`.

- [ ] **Step 3: Run browser QA**

Start `npm run dev -- --host 127.0.0.1`, then verify:

- `/ai-daily` at 390px, 768px, and 1440px.
- Original issue title remains visible above the lead-story title.
- Week/month/year trend switching, update metadata, coverage, and source links.
- `/ai-daily/2026-06-28` as an editorial issue.
- `/ai-daily/2026-06-23`, `/2026-06-25`, and `/2026-06-26` as signal archives.
- Light and dark themes.
- Mobile horizontal chapter navigation.
- Sticky desktop sidebar and active chapter state.
- No page-level horizontal overflow.
- Links, tables, code blocks, focus states, and reduced motion.

- [ ] **Step 4: Review and commit scoped remaining changes**

Review `git diff` and separate:

1. AI Daily UI/parser/history changes produced by this plan.
2. Pre-existing generator and RSS changes already present before this plan.
3. The four pre-existing full-repository ESLint failures in shadcn exports and `useTheme`.
4. Temporary `.superpowers/` visual companion files, which must not be committed.

Commit only reviewed files with a message that states the actual scope, for example:

```bash
git commit -m "feat: ship responsive AI daily editorial layout"
```

- [ ] **Step 5: Push with a clear change note**

After the user confirms the final diff, push the current branch and report:

- commits and hashes;
- files and behavior changed;
- desktop/mobile checks completed;
- historical issues normalized;
- any pre-existing uncommitted changes intentionally left out.
