import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { getPost } from '@/lib/posts'
import { GiscusComments } from '@/components/blog/GiscusComments'

export function BlogPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = slug ? getPost(slug) : null

  const headings = useMemo(() => {
    if (!post) return []
    const regex = /^(#{1,3})\s+(.+)$/gm
    const result: { level: number; text: string; id: string }[] = []
    let match
    while ((match = regex.exec(post.content)) !== null) {
      const level = match[1].length
      const text = match[2]
      const id = text
        .toLowerCase()
        .replace(/[^\w\u4e00-\u9fff]+/g, '-')
        .replace(/^-|-$/g, '')
      result.push({ level, text, id })
    }
    return result
  }, [post])

  if (!post) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-24 text-center">
        <h1 className="text-2xl font-bold mb-4">文章未找到</h1>
          <Button variant="outline" render={<Link to="/blog" />}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回博客
          </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-5xl px-4 py-12">
      <div className="flex gap-8">
        <article className="flex-1 min-w-0 max-w-3xl mx-auto">
          <Button variant="ghost" size="sm" className="mb-6" render={<Link to="/blog" />}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            返回博客
          </Button>

          <h1 className="text-3xl font-bold tracking-tight mb-3">{post.title}</h1>

          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground mb-6">
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {post.date}
            </span>
            {post.tags && post.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {post.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <Separator className="mb-8" />

          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {post.content}
          </ReactMarkdown>

          <Separator className="my-8" />

          <GiscusComments />
        </article>

        {headings.length > 0 && (
          <aside className="hidden lg:block w-52 shrink-0">
            <div className="sticky top-20">
              <h4 className="text-sm font-semibold mb-3">目录</h4>
              <ScrollArea className="h-[calc(100vh-10rem)]">
                <nav className="text-sm">
                  {headings.map((heading) => (
                    <a
                      key={heading.id}
                      href={`#${heading.id}`}
                      className="block py-1 text-muted-foreground hover:text-foreground transition-colors"
                      style={{ paddingLeft: `${(heading.level - 1) * 12}px` }}
                    >
                      {heading.text}
                    </a>
                  ))}
                </nav>
              </ScrollArea>
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}
