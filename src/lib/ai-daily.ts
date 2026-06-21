export interface AiDailyMeta {
  slug: string
  title: string
  date: string
  description: string
}

export interface AiDailyPost extends AiDailyMeta {
  content: string
}

function parseFrontmatter(raw: string): { data: Record<string, unknown>; content: string } {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/)
  if (!match) return { data: {}, content: raw }

  const yaml = match[1]
  const content = raw.slice(match[0].length)
  const data: Record<string, unknown> = {}

  let currentKey = ''
  let currentArray: string[] = []

  for (const line of yaml.split('\n')) {
    const listMatch = line.match(/^\s+-\s+(.+)/)
    if (listMatch && currentKey) {
      currentArray.push(listMatch[1])
      continue
    }

    if (currentKey && currentArray.length > 0) {
      data[currentKey] = currentArray
      currentArray = []
    }

    const keyValue = line.match(/^(\w[\w-]*)\s*:\s*(.+)/)
    if (keyValue) {
      currentKey = keyValue[1]
      const value = keyValue[2].trim()
      if (value === '') {
        currentArray = []
      } else {
        data[currentKey] = value
        currentKey = ''
      }
    }
  }

  if (currentKey && currentArray.length > 0) {
    data[currentKey] = currentArray
  }

  return { data, content }
}

const markdownModules = import.meta.glob('../content/ai-daily/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
})

function getRawContent(slug: string): string | null {
  const key = `../content/ai-daily/${slug}.md`
  return (markdownModules[key] as string) || null
}

export function getAiDailyPosts(): AiDailyMeta[] {
  const posts: AiDailyMeta[] = []

  for (const [filePath, raw] of Object.entries(markdownModules)) {
    const slug = filePath.replace('../content/ai-daily/', '').replace(/\.md$/, '')
    const { data } = parseFrontmatter(raw as string)

    posts.push({
      slug,
      title: (data.title as string) || slug,
      date: data.date
        ? new Date(data.date as string).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })
        : '',
      description: (data.description as string) || '',
    })
  }

  return posts.sort((a, b) => {
    if (!a.date) return 1
    if (!b.date) return -1
    return new Date(b.date).getTime() - new Date(a.date).getTime()
  })
}

export function getAiDailyPost(slug: string): AiDailyPost | null {
  const raw = getRawContent(slug)
  if (!raw) return null

  const { data, content } = parseFrontmatter(raw)

  return {
    slug,
    title: (data.title as string) || slug,
    date: data.date
      ? new Date(data.date as string).toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })
      : '',
    description: (data.description as string) || '',
    content,
  }
}
