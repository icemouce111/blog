import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useState, useMemo, useEffect } from 'react'
import { ArrowLeft, Calendar, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { getAiDailyPost } from '@/lib/ai-daily'

export function AiDailyPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = slug ? getAiDailyPost(slug) : null
  const [activeSection, setActiveSection] = useState('')

  // Extract section headers for TOC
  const toc = useMemo(() => {
    if (!post) return []
    const matches = post.content.matchAll(/^## (\d+ .+)$/gm)
    return Array.from(matches).map(m => ({
      num: m[1].slice(0, 2),
      title: m[1].slice(3).trim(),
      href: m[1].trim().toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff-]/g, ''),
    }))
  }, [post])

  // Observe sections for TOC highlight
  useEffect(() => {
    if (!toc.length) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id)
            break
          }
        }
      },
      { rootMargin: '-80px 0px -60% 0px' }
    )
    for (const item of toc) {
      const el = document.getElementById(item.href)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [toc])

  if (!post) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-24 text-center">
        <h1 className="text-2xl font-bold mb-4">日报未找到</h1>
        <Button variant="outline" render={<Link to="/ai-daily" />}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回 AI 日报
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-3xl px-4 py-12">
      <Button variant="ghost" size="sm" className="mb-6" render={<Link to="/ai-daily" />}>
        <ArrowLeft className="h-4 w-4 mr-1" />
        返回 AI 日报
      </Button>

      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-5 w-5 text-orange-500" />
        <span className="text-sm text-orange-500 font-medium">AI 日报</span>
      </div>

      <h1 className="text-3xl font-bold tracking-tight mb-3">{post.title}</h1>

      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
        <Calendar className="h-3.5 w-3.5" />
        {post.date}
      </div>

      <Separator className="mb-8" />

      <div className="relative flex gap-8 max-w-6xl mx-auto px-4 py-12">
        {/* Main content */}
        <article className="flex-1 min-w-0 max-w-3xl">
          <Button variant="ghost" size="sm" className="mb-6" render={<Link to="/ai-daily" />}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            返回 AI 日报
          </Button>

          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-5 w-5 text-orange-500" />
            <span className="text-sm text-orange-500 font-medium">AI 日报</span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight mb-2">{post.title}</h1>

          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6">
            <Calendar className="h-3 w-3" />
            {post.date}
          </div>

          <Separator className="mb-6" />

          <div className="prose prose-neutral dark:prose-invert max-w-none
            prose-sm
            prose-headings:scroll-mt-20 prose-headings:text-base prose-headings:font-semibold prose-headings:mt-8 prose-headings:mb-3
            prose-h2:border-b prose-h2:border-border/50 prose-h2:pb-2
            prose-p:text-sm prose-p:leading-relaxed prose-p:my-2
            prose-a:text-orange-500 hover:prose-a:text-orange-600 prose-a:font-medium
            prose-strong:text-foreground
            prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
            prose-pre:bg-muted prose-pre:border prose-pre:text-xs
            prose-blockquote:border-orange-500/50 prose-blockquote:text-muted-foreground prose-blockquote:text-sm prose-blockquote:my-3
            prose-hr:border-border prose-hr:my-6
            prose-li:text-sm prose-li:my-1
            prose-ul:my-2">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2: ({ children, ...props }) => {
                  const id = String(children).toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff-]/g, '')
                  return <h2 id={id} {...props}>{children}</h2>
                },
              }}
            >
              {post.content.replace(/^## /gm, '## ')}
            </ReactMarkdown>
          </div>
        </article>

        {/* TOC sidebar */}
        {toc.length > 0 && (
          <aside className="hidden lg:block w-56 shrink-0">
            <div className="sticky top-24">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                目录
              </h4>
              <nav className="space-y-1">
                {toc.map((item) => (
                  <a
                    key={item.href}
                    href={'#' + item.href}
                    onClick={(e) => {
                      e.preventDefault()
                      document.getElementById(item.href)?.scrollIntoView({ behavior: 'smooth' })
                    }}
                    className={`
                      block text-xs py-1 px-2 rounded transition-colors
                      ${activeSection === item.href
                        ? 'bg-orange-500/10 text-orange-600 font-medium'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                      }
                    `}
                  >
                    {item.num} {item.title}
                  </a>
                ))}
              </nav>
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}
