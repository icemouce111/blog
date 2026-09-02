import { useMemo } from 'react'
import type { ComponentPropsWithoutRef, ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { GiscusComments } from '@/components/blog/GiscusComments'
import { PageContainer } from '@/components/layout/PageContainer'
import { getPost } from '@/lib/posts'

function headingId(children: ReactNode) {
  return String(children)
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff]+/g, '-')
    .replace(/^-|-$/g, '')
}

const markdownComponents = {
  h2: ({ children, ...props }: ComponentPropsWithoutRef<'h2'>) => (
    <h2 id={headingId(children)} {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }: ComponentPropsWithoutRef<'h3'>) => (
    <h3 id={headingId(children)} {...props}>{children}</h3>
  ),
}

export function BlogPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = slug ? getPost(slug) : null

  const headings = useMemo(() => {
    if (!post) return []
    const regex = /^(#{2,3})\s+(.+)$/gm
    const result: { level: number; text: string; id: string }[] = []
    let match
    while ((match = regex.exec(post.content)) !== null) {
      const text = match[2]
      result.push({
        level: match[1].length,
        text,
        id: text.toLowerCase().replace(/[^\w\u4e00-\u9fff]+/g, '-').replace(/^-|-$/g, ''),
      })
    }
    return result
  }, [post])

  if (!post) {
    return (
      <div className="site-page">
        <PageContainer size="narrow" className="py-24 text-center">
          <div className="site-panel p-12">
            <h1 className="mb-4 text-2xl font-bold">文章未找到</h1>
            <Button variant="outline" render={<Link to="/blog" />}>
              <ArrowLeft className="h-4 w-4" /> 返回博客
            </Button>
          </div>
        </PageContainer>
      </div>
    )
  }

  const contentWithoutRepeatedTitle = post.content.replace(/^\s*#\s+.+\n+/, '')

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <div className="site-article-layout">
          {headings.length > 0 && (
            <aside className="site-article-nav sticky top-20">
              <p className="site-eyebrow mb-3">CONTENTS</p>
              <ScrollArea className="max-h-[calc(100vh-10rem)]">
                <nav className="text-sm">
                  {headings.map((heading) => (
                    <a
                      key={heading.id}
                      href={`#${heading.id}`}
                      className="block text-muted-foreground transition-colors hover:text-foreground"
                      style={{ paddingLeft: `${(heading.level - 2) * 12}px` }}
                    >
                      {heading.text}
                    </a>
                  ))}
                </nav>
              </ScrollArea>
            </aside>
          )}

          <article className="site-article min-w-0">
            <header className="site-article-header">
              <Link className="inline-flex items-center gap-1 text-sm text-muted-foreground" to="/blog">
                <ArrowLeft className="h-4 w-4" /> 返回博客
              </Link>
              <h1>{post.title}</h1>
              <p className="max-w-2xl text-muted-foreground">{post.description}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{post.date}</span>
                <div className="flex flex-wrap gap-1.5">
                  {post.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
                </div>
              </div>
            </header>

            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {contentWithoutRepeatedTitle}
            </ReactMarkdown>

            <div className="mt-10 border-t pt-8">
              <GiscusComments />
            </div>
          </article>
        </div>
      </PageContainer>
    </div>
  )
}
