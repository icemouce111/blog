import matter from 'gray-matter'

export interface PostMeta {
  slug: string
  title: string
  date: string
  description: string
  tags: string[]
  cover?: string
}

export interface Post extends PostMeta {
  content: string
}

const markdownModules = import.meta.glob('../content/blog/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
})

function getRawContent(slug: string): string | null {
  const key = `../content/blog/${slug}.md`
  return (markdownModules[key] as string) || null
}

export function getPosts(): PostMeta[] {
  const posts: PostMeta[] = []

  for (const [filePath, raw] of Object.entries(markdownModules)) {
    const slug = filePath.replace('../content/blog/', '').replace(/\.md$/, '')
    const { data } = matter(raw as string)

    posts.push({
      slug,
      title: data.title || slug,
      date: data.date
        ? new Date(data.date).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })
        : '',
      description: data.description || '',
      tags: data.tags || [],
      cover: data.cover || undefined,
    })
  }

  return posts.sort((a, b) => {
    if (!a.date) return 1
    if (!b.date) return -1
    return new Date(b.date).getTime() - new Date(a.date).getTime()
  })
}

export function getPost(slug: string): Post | null {
  const raw = getRawContent(slug)
  if (!raw) return null

  const { data, content } = matter(raw)

  return {
    slug,
    title: data.title || slug,
    date: data.date
      ? new Date(data.date).toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })
      : '',
    description: data.description || '',
    tags: data.tags || [],
    cover: data.cover || undefined,
    content,
  }
}

export function getAllTags(): string[] {
  const posts = getPosts()
  const tagSet = new Set<string>()
  posts.forEach((post) => post.tags?.forEach((tag) => tagSet.add(tag)))
  return Array.from(tagSet).sort()
}
