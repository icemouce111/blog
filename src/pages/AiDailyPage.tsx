import { Link } from 'react-router-dom'
import { Newspaper, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { getAiDailyReports } from '@/lib/ai-daily-posts'

export function AiDailyPage() {
  const reports = getAiDailyReports()

  return (
    <div className="container mx-auto max-w-5xl px-4 py-12">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Newspaper className="h-6 w-6 text-blue-500" />
          <h1 className="text-3xl font-bold tracking-tight">AI 日报</h1>
        </div>
        <p className="text-muted-foreground">每日 AI 行业动态汇总，自动生成</p>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          暂无日报内容
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reports.map((report) => (
            <Link key={report.slug} to={`/ai-daily/${report.slug}`}>
              <Card className="h-full transition-colors hover:border-blue-500/50">
                <CardHeader>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>{report.date}</span>
                  </div>
                  <CardTitle className="text-lg">{report.title}</CardTitle>
                  <CardDescription className="text-sm">
                    {report.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <span className="text-sm text-blue-500 flex items-center gap-1 group-hover:text-blue-600 transition-colors">
                    阅读详情 →
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
