import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Fuse from 'fuse.js'
import { ArrowUpRight, BookOpen, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { getAllTags, getPosts, type PostMeta } from '@/lib/posts'
import { PageContainer } from '@/components/layout/PageContainer'
import { SectionHero } from '@/components/layout/SectionHero'

export function BlogPage() {
  const posts = getPosts()
  const allTags = getAllTags()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  const fuse = useMemo(() => new Fuse(posts, {
    keys: ['title', 'description', 'tags'],
    threshold: 0.3,
  }), [posts])

  const filteredPosts = useMemo(() => {
    let result: PostMeta[] = posts
    if (searchQuery.trim()) result = fuse.search(searchQuery.trim()).map((item) => item.item)
    if (selectedTag) result = result.filter((post) => post.tags?.includes(selectedTag))
    return result
  }, [fuse, posts, searchQuery, selectedTag])

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <SectionHero
          eyebrow="WRITING / NOTES"
          title="博客"
          description="记录 Agent 工程、AI 产品实践，以及一个真实问题如何被拆解和解决。"
          icon={BookOpen}
          meta={`${posts.length} 篇文章`}
          tone="violet"
        />

        <div className="site-panel site-filter-panel">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="搜索文章、标签或问题…"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="site-search pl-10"
            />
          </div>
          {allTags.length > 0 && (
            <div className="site-filter-tags" aria-label="按标签筛选">
              <Badge
                variant={selectedTag === null ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setSelectedTag(null)}
              >
                全部
              </Badge>
              {allTags.map((tag) => (
                <Badge
                  key={tag}
                  variant={selectedTag === tag ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
                >
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {filteredPosts.length === 0 ? (
          <div className="site-panel py-16 text-center text-muted-foreground">没有找到相关文章</div>
        ) : (
          <div className="site-blog-grid site-tone-violet">
            {filteredPosts.map((post, index) => (
              <Link key={post.slug} to={`/blog/${post.slug}`}>
                <Card className="site-card site-blog-card">
                  <CardHeader>
                    <div className="flex items-center justify-between gap-4">
                      <span className="site-card-index">{String(index + 1).padStart(2, '0')}</span>
                      <time className="text-xs text-muted-foreground">{post.date}</time>
                    </div>
                    <CardTitle className="line-clamp-2">{post.title}</CardTitle>
                    <CardDescription className="line-clamp-3">{post.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="mt-auto">
                    <div className="flex flex-wrap gap-1.5">
                      {post.tags.map((tag) => <span className="site-chip" key={tag}>{tag}</span>)}
                    </div>
                    <div className="site-blog-card-footer">
                      <span>阅读全文</span><ArrowUpRight className="h-4 w-4" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </PageContainer>
    </div>
  )
}
