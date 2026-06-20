import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft, Calendar } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { getAiDailyReport } from '@/lib/ai-daily-posts'

export function AiDailyPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const report = slug ? getAiDailyReport(slug) : null

  if (!report) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-24 text-center">
        <h1 className="text-2xl font-bold mb-4">日报未找到</h1>
          <Button variant="outline" render={<Link to="/ai-daily" />}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回日报列表
          </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-3xl px-4 py-12">
      <Button variant="ghost" size="sm" className="mb-6" render={<Link to="/ai-daily" />}>
        <ArrowLeft className="h-4 w-4 mr-1" />
        返回日报列表
      </Button>

      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
        <Calendar className="h-3.5 w-3.5" />
        <span>{report.date}</span>
      </div>

      <h1 className="text-3xl font-bold tracking-tight mb-6">{report.title}</h1>

      <Separator className="mb-8" />

      <article className="prose-custom">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {report.content}
        </ReactMarkdown>
      </article>

      <Separator className="my-8" />

      <div className="text-center text-sm text-muted-foreground">
        <p>AI 日报由自动化系统每日生成，信息来源于多个公开来源。</p>
      </div>
    </div>
  )
}
