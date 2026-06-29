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

interface FirstListItem {
  raw: string
  remainingMarkdown: string
}

const listItemPattern = /^\s{0,3}(?:\d+\.|[-*+])\s+/
const urlPattern = /https?:\/\/[^\s)>\]]+/g

function unquoteYamlScalar(value: string) {
  const trimmed = value.trim()
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

export function parseFrontmatter(raw: string): {
  data: Record<string, unknown>
  content: string
} {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/)
  if (!match) return { data: {}, content: raw }

  const data: Record<string, unknown> = {}
  let arrayKey = ''
  let arrayValue: string[] = []

  for (const line of match[1].split('\n')) {
    const listMatch = line.match(/^\s+-\s+(.+)/)
    if (listMatch && arrayKey) {
      arrayValue.push(unquoteYamlScalar(listMatch[1]))
      continue
    }

    if (arrayKey) {
      data[arrayKey] = arrayValue
      arrayKey = ''
      arrayValue = []
    }

    const keyValue = line.match(/^(\w[\w-]*)\s*:\s*(.*)$/)
    if (!keyValue) continue
    const value = keyValue[2].trim()
    if (value) {
      data[keyValue[1]] = unquoteYamlScalar(value)
    } else {
      arrayKey = keyValue[1]
    }
  }

  if (arrayKey) {
    data[arrayKey] = arrayValue
  }

  return { data, content: raw.slice(match[0].length) }
}

export function isAiDailySlug(slug: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(slug)
}

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

function createSectionId(number: string, title: string) {
  return `${number}-${title}`
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\u4e00-\u9fff-]/g, '')
}

function cleanSectionTitle(title: string) {
  return title.replace(/^[^\p{L}\p{N}]+/u, '').trim()
}

function extractFirstListItem(markdown: string): FirstListItem | null {
  const lines = markdown.split('\n')
  const start = lines.findIndex((line) => listItemPattern.test(line))
  if (start < 0) return null

  let end = start + 1
  while (end < lines.length) {
    const line = lines[end]
    if (listItemPattern.test(line) || /^#{2,3}\s+/.test(line) || /^---\s*$/.test(line)) {
      break
    }
    end += 1
  }

  return {
    raw: lines.slice(start, end).join('\n').trim(),
    remainingMarkdown: [...lines.slice(0, start), ...lines.slice(end)].join('\n').trim(),
  }
}

function parseLeadStory(raw: string): AiDailyLeadStory {
  const firstLine = raw.split('\n')[0].replace(listItemPattern, '').trim()
  const title = raw.match(/\*\*(.+?)\*\*/)?.[1]?.trim() || firstLine
  const confidenceMatch = raw.match(/\*\*\[([^\]]+)\]\*\*|\[([^\]]*置信度|单源信号)\]/)
  const confidence = confidenceMatch?.[1] || confidenceMatch?.[2] || ''
  const sourceUrl = raw.match(urlPattern)?.[0] || ''
  const summaryMarkdown = raw
    .replace(listItemPattern, '')
    .replace(/\*\*(.+?)\*\*/, '')
    .replace(/\*\*\[[^\]]+\]\*\*|\[[^\]]*(?:置信度|单源信号)\]/g, '')
    .replace(/\[链接\]\(https?:\/\/[^)]+\)/g, '')
    .replace(urlPattern, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return { title, summaryMarkdown, confidence, sourceUrl }
}

function extractSections(content: string) {
  const numberedHeadings = [...content.matchAll(/^##\s+(\d{2})\s+(.+)$/gm)]

  return numberedHeadings.map((match) => {
    const bodyStart = (match.index ?? 0) + match[0].length
    const nextHeading = content.slice(bodyStart).search(/\n##\s+/)
    const bodyEnd = nextHeading >= 0 ? bodyStart + nextHeading : content.length
    const title = cleanSectionTitle(match[2])

    return {
      number: match[1],
      title,
      id: createSectionId(match[1], title),
      markdown: content
        .slice(bodyStart, bodyEnd)
        .trim()
        .replace(/\n---\s*$/, '')
        .trim(),
    }
  })
}

export function parseAiDailyContent(content: string): ParsedAiDailyContent {
  const footer = content.match(/^\*本日报[\s\S]*?\*$/m)?.[0] || ''
  const editorialContent = footer
    ? content
        .slice(0, content.indexOf(footer))
        .replace(/\n---\s*$/, '')
        .trimEnd()
    : content
  const sections = extractSections(editorialContent)
  const originalSectionMarkdown = sections.map((section) => section.markdown)
  const firstItem = sections[0] ? extractFirstListItem(sections[0].markdown) : null
  const leadStory = firstItem ? parseLeadStory(firstItem.raw) : null

  if (sections[0] && firstItem) {
    sections[0] = { ...sections[0], markdown: firstItem.remainingMarkdown }
  }

  const urls = (editorialContent.match(urlPattern) || []).map((url) =>
    url.replace(/[.,;:]+$/, '')
  )
  const storyCount = originalSectionMarkdown.reduce(
    (total, markdown) =>
      total + markdown.split('\n').filter((line) => listItemPattern.test(line)).length,
    0
  )
  const readableContent = editorialContent.replace(/[#>*_`|:[\]()!-]/g, ' ')
  const readableUnits =
    (readableContent.match(/[\u4e00-\u9fff]/g)?.length || 0) +
    (readableContent.match(/[A-Za-z0-9]+/g)?.length || 0)
  return {
    sections,
    leadStory,
    storyCount,
    sourceCount: new Set(urls).size,
    readingMinutes: Math.max(1, Math.ceil(readableUnits / 500)),
    isSignalArchive: sections[0]?.title.includes('原始信号归档') || false,
    footer,
    fallbackMarkdown: sections.length ? '' : editorialContent.trim(),
  }
}
