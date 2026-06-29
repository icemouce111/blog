import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parseAiTrendData } from '../src/lib/ai-trends.ts'

function createWindow(window: 'week' | 'month' | 'year') {
  return {
    window,
    rangeStart: '2026-06-01',
    rangeEnd: '2026-06-29',
    updatedAt: '2026-06-29T09:00:00+08:00',
    coverageCount: 8,
    mode: 'curated',
    insights: Array.from({ length: 3 }, (_, index) => ({
      title: `趋势 ${index + 1}`,
      summary: '有证据支持的应用趋势判断。',
      sources: [{
        title: 'Source',
        url: `https://example.com/${window}/${index}`,
        publishedAt: '2026-06-20',
      }],
    })),
  }
}

test('accepts three sourced insights for every valid time window', () => {
  const data = parseAiTrendData({
    windows: [createWindow('week'), createWindow('month'), createWindow('year')],
  })

  assert.equal(data.windows.length, 3)
  assert.equal(data.windows[0].insights.length, 3)
})

test('drops invalid windows instead of rendering unsourced claims', () => {
  const invalid = createWindow('week')
  invalid.insights[0].sources = []

  const data = parseAiTrendData({ windows: [invalid] })

  assert.equal(data.windows.length, 0)
})

test('drops duplicate and unknown time windows', () => {
  const week = createWindow('week')
  const data = parseAiTrendData({
    windows: [week, week, { ...createWindow('month'), window: 'quarter' }],
  })

  assert.deepEqual(data.windows.map((item) => item.window), ['week'])
})

test('accepts the checked-in curated trend snapshot', () => {
  const seedPath = new URL('../src/data/ai-trends.json', import.meta.url)
  const seed = JSON.parse(readFileSync(seedPath, 'utf8'))
  const data = parseAiTrendData(seed)

  assert.deepEqual(data.windows.map((item) => item.window), ['week', 'month', 'year'])
  assert.ok(data.windows.every((item) => item.insights.length === 3))
})
