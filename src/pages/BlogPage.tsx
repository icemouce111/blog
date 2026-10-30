import { useMemo, useState } from 'react'
import Fuse from 'fuse.js'
import { BookOpen, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ContentList } from '@/components/reading/ContentList'
import { Badge } from '@/components/ui/badge'
import { getAllTags, getPosts, type PostMeta } from '@/lib/posts'
import { PageContainer } from '@/components/layout/PageContainer'
import { SectionHero } from '@/components/layout/SectionHero'

export function BlogPage() {
  const posts = useMemo(() => getPosts(), [])
  const allTags = useMemo(() => getAllTags(), [])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  const fuse = useMemo(
    () =>
      new Fuse(posts, {
        keys: ['title', 'description', 'tags'],
        threshold: 0.3,
      }),
    [posts],
  )

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
              aria-label="搜索文章"
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
                render={<button type="button" aria-pressed={selectedTag === null} />}
                variant={selectedTag === null ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setSelectedTag(null)}
              >
                全部
              </Badge>
              {allTags.map((tag) => (
                <Badge
                  render={<button type="button" aria-pressed={selectedTag === tag} />}
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

        <p className="site-filter-count" role="status">
          {filteredPosts.length} 篇文章
        </p>
        {filteredPosts.length === 0 ? (
          <div className="site-panel py-16 text-center text-muted-foreground">没有找到相关文章</div>
        ) : (
          <ContentList posts={filteredPosts} />
        )}
      </PageContainer>
    </div>
  )
}
