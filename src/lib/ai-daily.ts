import {
  createIssueId,
  createIssueNavigation,
  isAiDailySlug,
  parseAiDailyContent,
  parseFrontmatter,
  type ParsedAiDailyContent,
} from './ai-daily-parser'

export interface AiDailyMeta {
  slug: string
  title: string
  date: string
  dateISO: string
  description: string
  issueId: string
  leadTitle: string
  leadSummary: string
  storyCount: number
  sourceCount: number
  readingMinutes: number
  isSignalArchive: boolean
}

export interface AiDailyPost extends AiDailyMeta {
  content: string
  parsed: ParsedAiDailyContent
  newerSlug: string | null
  olderSlug: string | null
}

interface AiDailyRecord extends AiDailyMeta {
  content: string
  parsed: ParsedAiDailyContent
}

const markdownModules = import.meta.glob('../content/ai-daily/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
})

function formatDate(dateISO: string) {
  if (!dateISO) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Asia/Shanghai',
  }).format(new Date(`${dateISO}T00:00:00+08:00`))
}

function createRecord(filePath: string, raw: string): AiDailyRecord | null {
  const slug = filePath.replace('../content/ai-daily/', '').replace(/\.md$/, '')
  if (!isAiDailySlug(slug)) return null

  const { data, content } = parseFrontmatter(raw)
  const dateISO = (data.date as string) || slug
  const parsed = parseAiDailyContent(content)
  const archiveLeadTitle = `今天值得知道的 ${parsed.storyCount} 个 AI 信号`
  const archiveLeadSummary = '今天先为你整理可追溯的来源速览；开源项目和可参与的官方机会已单独整理。'

  return {
    slug,
    title: (data.title as string) || `AI 行动情报站 - ${dateISO}`,
    date: formatDate(dateISO),
    dateISO,
    description: (data.description as string) || '',
    issueId: createIssueId(dateISO),
    leadTitle: parsed.isSignalArchive
      ? archiveLeadTitle
      : parsed.leadStory?.title || (data.title as string) || slug,
    leadSummary: parsed.isSignalArchive
      ? archiveLeadSummary
      : parsed.leadStory?.summaryMarkdown || (data.description as string) || '',
    storyCount: parsed.storyCount,
    sourceCount: parsed.sourceCount,
    readingMinutes: parsed.readingMinutes,
    isSignalArchive: parsed.isSignalArchive,
    content,
    parsed,
  }
}

const records = Object.entries(markdownModules)
  .map(([filePath, raw]) => createRecord(filePath, raw as string))
  .filter((record): record is AiDailyRecord => record !== null)
  .toSorted((a, b) => b.dateISO.localeCompare(a.dateISO))

function toMeta(record: AiDailyRecord): AiDailyMeta {
  return {
    slug: record.slug,
    title: record.title,
    date: record.date,
    dateISO: record.dateISO,
    description: record.description,
    issueId: record.issueId,
    leadTitle: record.leadTitle,
    leadSummary: record.leadSummary,
    storyCount: record.storyCount,
    sourceCount: record.sourceCount,
    readingMinutes: record.readingMinutes,
    isSignalArchive: record.isSignalArchive,
  }
}

export function getAiDailyPosts(): AiDailyMeta[] {
  return records.map(toMeta)
}

export function getAiDailyPost(slug: string): AiDailyPost | null {
  const record = records.find((item) => item.slug === slug)
  if (!record) return null

  const navigation = createIssueNavigation(
    records.map((item) => item.slug),
    slug
  )

  return {
    ...toMeta(record),
    content: record.content,
    parsed: record.parsed,
    newerSlug: navigation.newer,
    olderSlug: navigation.older,
  }
}
