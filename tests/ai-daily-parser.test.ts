import assert from 'node:assert/strict'
import test from 'node:test'
import { isAiDailySlug, parseAiDailyContent } from '../src/lib/ai-daily-parser.ts'

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
  assert.equal(result.sections[0].title, '今日头条')
  assert.equal(result.leadStory?.title, '模型推理进入新阶段')
  assert.equal(result.leadStory?.confidence, '高置信度')
  assert.equal(result.leadStory?.sourceUrl, 'https://example.com/lead')
  assert.equal(result.storyCount, 3)
  assert.equal(result.sourceCount, 2)
  assert.equal(result.isSignalArchive, false)
  assert.match(result.sections[0].markdown, /第二条新闻/)
  assert.doesNotMatch(result.sections[0].markdown, /模型推理进入新阶段/)
})

test('recognizes a numbered signal archive and indented source items', () => {
  const result = parseAiDailyContent(`
## 01 📡 原始信号归档

### Hacker News
  1. **A raw signal** [链接](https://example.com/raw)
     score=100

  2. **Another signal**
`)

  assert.equal(result.isSignalArchive, true)
  assert.equal(result.sections[0].title, '原始信号归档')
  assert.equal(result.leadStory?.title, 'A raw signal')
  assert.equal(result.storyCount, 2)
  assert.match(result.sections[0].markdown, /### Hacker News/)
})

test('falls back to the original markdown when numbered sections are absent', () => {
  const markdown = '## Notes\n\nUnstructured content'
  const result = parseAiDailyContent(markdown)

  assert.equal(result.sections.length, 0)
  assert.equal(result.fallbackMarkdown, markdown)
})

test('accepts only date-shaped daily slugs', () => {
  assert.equal(isAiDailySlug('2026-06-28'), true)
  assert.equal(isAiDailySlug('TEMPLATE'), false)
  assert.equal(isAiDailySlug('2026-6-28'), false)
})
