import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useState, useMemo, useEffect } from 'react'
import { ArrowLeft, Calendar, Sparkles, Target, DollarSign, MousePointerClick, GitCompare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getAiDailyPost } from '@/lib/ai-daily'
import { PageContainer } from '@/components/layout/PageContainer'

const pmFramework = [
  {
    icon: Target,
    label: 'PMF 产品市场契合',
    color: 'text-blue-500',
    bg: 'bg-blue-500/5',
    border: 'border-blue-500/20',
    questions: [
      '解决了谁的什么问题？',
      '是刚需还是"有点意思"？',
      '比同类产品好在哪？',
    ],
  },
  {
    icon: DollarSign,
    label: '商业模型',
    color: 'text-green-500',
    bg: 'bg-green-500/5',
    border: 'border-green-500/20',
    questions: [
      '开源还是闭源？怎么赚钱？',
      '社区驱动还是销售驱动？',
      '背后有公司/融资吗？',
    ],
  },
  {
    icon: MousePointerClick,
    label: 'UX/DX 体验',
    color: 'text-purple-500',
    bg: 'bg-purple-500/5',
    border: 'border-purple-500/20',
    questions: [
      '上手门槛高不高？',
      '文档写得好不好？',
      '3步跑通还是半天配置？',
    ],
  },
  {
    icon: GitCompare,
    label: '竞争定位',
    color: 'text-orange-500',
    bg: 'bg-orange-500/5',
    border: 'border-orange-500/20',
    questions: [
      '这个赛道还有谁？',
      '怎么差异化？',
      '场景重叠在哪？差异在哪？',
    ],
  },
] as const

export function AiDailyPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = slug ? getAiDailyPost(slug) : null
  const [activeSection, setActiveSection] = useState('')

  const toc = useMemo(() => {
    if (!post) return []
    const matches = post.content.matchAll(/^## (\d+ .+)$/gm)
    return Array.from(matches).map((m) => ({
      num: m[1].slice(0, 2),
      title: m[1].slice(3).trim(),
      href: m[1].trim().toLowerCase().replace(/\s+/g, '-').replace(/[^\w\u4e00-\u9fff-]/g, ''),
    }))
  }, [post])

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
      <PageContainer size="narrow" className="py-24 text-center">
        <h1 className="text-2xl font-bold mb-4">日报未找到</h1>
        <Button variant="outline" render={<Link to="/ai-daily" />}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回 AI 日报
        </Button>
      </PageContainer>
    )
  }

  return (
    <PageContainer size="wide">
      <div className="flex gap-8">
        {toc.length > 0 && (
          <aside className="hidden lg:block w-64 shrink-0">
            <div className="sticky top-24">
              <h4 className="text-xl font-bold mb-5">目录</h4>
              <nav className="space-y-1.5">
                {toc.map((item) => (
                  <a
                    key={item.href}
                    href={`#${item.href}`}
                    onClick={(e) => {
                      e.preventDefault()
                      document.getElementById(item.href)?.scrollIntoView({ behavior: 'smooth' })
                    }}
                    className={
                      activeSection === item.href
                        ? 'block text-sm py-1.5 px-3 rounded-lg transition-colors bg-orange-500/10 text-orange-600 font-medium'
                        : 'block text-sm py-1.5 px-3 rounded-lg transition-colors text-muted-foreground hover:text-foreground hover:bg-muted'
                    }
                  >
                    {item.num} {item.title}
                  </a>
                ))}
              </nav>
            </div>
          </aside>
        )}

        <article className="flex-1 min-w-0">
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

          <div
            className="prose prose-neutral dark:prose-invert max-w-none
            prose-sm
            prose-headings:scroll-mt-24 prose-headings:text-base prose-headings:font-semibold prose-headings:mt-8 prose-headings:mb-3
            prose-h2:border-b prose-h2:border-border/50 prose-h2:pb-2
            prose-p:text-sm prose-p:leading-relaxed prose-p:my-2
            prose-a:text-orange-500 hover:prose-a:text-orange-600 prose-a:font-medium
            prose-strong:text-foreground
            prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
            prose-pre:bg-muted prose-pre:border prose-pre:text-xs
            prose-blockquote:border-orange-500/50 prose-blockquote:text-muted-foreground prose-blockquote:text-sm prose-blockquote:my-3
            prose-hr:border-border prose-hr:my-6
            prose-li:text-sm prose-li:my-1
            prose-ul:my-2"
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2: ({ children, ...props }) => {
                  const id = String(children)
                    .toLowerCase()
                    .replace(/\s+/g, '-')
                    .replace(/[^\w\u4e00-\u9fff-]/g, '')
                  return (
                    <h2 id={id} {...props}>
                      {children}
                    </h2>
                  )
                },
              }}
            >
              {post.content}
            </ReactMarkdown>

            <Separator className="my-8" />

            <div className="mb-8">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Target className="h-5 w-5 text-orange-500" />
                产品经理视角
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {pmFramework.map((item) => (
                  <Card key={item.label} className={`${item.bg} ${item.border} border`}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <item.icon className={`h-4 w-4 ${item.color}`} />
                        {item.label}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-1 text-xs text-muted-foreground">
                        {item.questions.map((q) => (
                          <li key={q} className="flex items-start gap-2">
                            <span className={`${item.color} mt-0.5 shrink-0`}>•</span>
                            {q}
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </article>
      </div>
    </PageContainer>
  )
}
