export interface GithubDailyRepo {
  rank: number
  fullName: string
  url: string
  description: string
  language: string
  stars: number | null
  starsToday: number | null
  forks: number | null
  topics: string[]
  what: string
  help: string
}

export interface GithubDailyHighlight {
  repo: string
  title: string
  why: string
  value: string
  how: string
}

export interface GithubDailyRecord {
  date: string
  generatedAt: string
  mode: 'analyzed' | 'fallback'
  intro: string
  repos: GithubDailyRepo[]
  highlights: GithubDailyHighlight[]
}

export interface GithubDailyPost extends GithubDailyRecord {
  slug: string
  dateDisplay: string
  newerSlug: string | null
  olderSlug: string | null
}

const recordModules = import.meta.glob('../data/github-daily/*.json', {
  import: 'default',
  eager: true,
}) as Record<string, GithubDailyRecord>

function formatDate(dateISO: string) {
  if (!dateISO) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Asia/Shanghai',
  }).format(new Date(`${dateISO}T00:00:00+08:00`))
}

const isRecordSlug = (slug: string) => /^\d{4}-\d{2}-\d{2}$/.test(slug)

const slugs = Object.keys(recordModules)
  .map((filePath) => filePath.replace('../data/github-daily/', '').replace(/\.json$/, ''))
  .filter(isRecordSlug)
  .sort((a, b) => b.localeCompare(a))

function createPost(slug: string, record: GithubDailyRecord): GithubDailyPost {
  const index = slugs.indexOf(slug)
  return {
    ...record,
    slug,
    dateDisplay: formatDate(record.date || slug),
    newerSlug: index > 0 ? slugs[index - 1] : null,
    olderSlug: index >= 0 && index < slugs.length - 1 ? slugs[index + 1] : null,
  }
}

const posts: GithubDailyPost[] = slugs
  .map((slug) => {
    const record = recordModules[`../data/github-daily/${slug}.json`]
    return record ? createPost(slug, record) : null
  })
  .filter((post): post is GithubDailyPost => post !== null)

export function getGithubDailyPosts(): GithubDailyPost[] {
  return posts
}

export function getGithubDailyPost(slug: string): GithubDailyPost | null {
  return posts.find((post) => post.slug === slug) ?? null
}

export function formatStars(stars: number | null): string {
  if (stars === null) return '—'
  if (stars >= 1000) return `${(stars / 1000).toFixed(1)}k`
  return String(stars)
}
