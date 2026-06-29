export type TrendWindow = 'week' | 'month' | 'year'
export type TrendMode = 'curated' | 'generated'

export interface TrendSource {
  title: string
  url: string
  publishedAt: string
}

export interface TrendInsight {
  title: string
  summary: string
  sources: TrendSource[]
}

export interface TrendSnapshot {
  window: TrendWindow
  rangeStart: string
  rangeEnd: string
  updatedAt: string
  coverageCount: number
  mode: TrendMode
  insights: TrendInsight[]
}

export interface AiTrendData {
  windows: TrendSnapshot[]
}

const validWindows = new Set<TrendWindow>(['week', 'month', 'year'])
const validModes = new Set<TrendMode>(['curated', 'generated'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function parseSource(value: unknown): TrendSource | null {
  if (!isRecord(value)) return null
  if (
    !isNonEmptyString(value.title) ||
    !isNonEmptyString(value.url) ||
    !/^https?:\/\//.test(value.url) ||
    !isNonEmptyString(value.publishedAt)
  ) {
    return null
  }

  return {
    title: value.title.trim(),
    url: value.url,
    publishedAt: value.publishedAt,
  }
}

function parseInsight(value: unknown): TrendInsight | null {
  if (!isRecord(value)) return null
  if (!isNonEmptyString(value.title) || !isNonEmptyString(value.summary)) return null
  if (!Array.isArray(value.sources) || value.sources.length === 0) return null

  const sources = value.sources.map(parseSource)
  if (sources.some((source) => source === null)) return null

  return {
    title: value.title.trim(),
    summary: value.summary.trim(),
    sources: sources as TrendSource[],
  }
}

function parseWindow(value: unknown): TrendSnapshot | null {
  if (!isRecord(value)) return null
  if (!isNonEmptyString(value.window) || !validWindows.has(value.window as TrendWindow)) {
    return null
  }
  if (!isNonEmptyString(value.mode) || !validModes.has(value.mode as TrendMode)) return null
  if (
    !isNonEmptyString(value.rangeStart) ||
    !isNonEmptyString(value.rangeEnd) ||
    !isNonEmptyString(value.updatedAt) ||
    typeof value.coverageCount !== 'number' ||
    value.coverageCount < 0 ||
    !Array.isArray(value.insights) ||
    value.insights.length !== 3
  ) {
    return null
  }

  const insights = value.insights.map(parseInsight)
  if (insights.some((insight) => insight === null)) return null

  return {
    window: value.window as TrendWindow,
    rangeStart: value.rangeStart,
    rangeEnd: value.rangeEnd,
    updatedAt: value.updatedAt,
    coverageCount: value.coverageCount,
    mode: value.mode as TrendMode,
    insights: insights as TrendInsight[],
  }
}

export function parseAiTrendData(value: unknown): AiTrendData {
  if (!isRecord(value) || !Array.isArray(value.windows)) return { windows: [] }

  const seen = new Set<TrendWindow>()
  const windows: TrendSnapshot[] = []

  for (const candidate of value.windows) {
    const parsed = parseWindow(candidate)
    if (!parsed || seen.has(parsed.window)) continue
    seen.add(parsed.window)
    windows.push(parsed)
  }

  return { windows }
}
