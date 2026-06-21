import { Link } from 'react-router-dom'
import { Sparkles, Calendar } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getAiDailyPosts } from '@/lib/ai-daily'

export function AiDailyPage() {
  const posts = getAiDailyPosts()

  return (
    <div className="container mx-auto max-w-3xl px-4 py-12">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-6 w-6 text-orange-500" />
          <h1 className="text-2xl font-bold tracking-tight">AI 日报</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          每日 AI 行业动态汇总 · 多分析师视角 · 技术趋势与机会洞察
        </p>
      </div>

      {posts.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-lg">暂无日报</CardTitle>
            <CardDescription>
              AI 日报功能正在搭建中，很快会在每天早上 7:30 自动生成。
            </CardDescription>
          </CardHeader>
        </Card>
       ) : (
        <div className="grid gap-4">
          {posts.map((post) => (
            <Card key={post.slug} className="hover:border-orange-500/50 transition-colors py-1">
              <Link to={`/ai-daily/${post.slug}`} className="block">
                <CardHeader>
                  <CardTitle className="text-base">{post.title}</CardTitle>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                    <Calendar className="h-3 w-3" />
                    {post.date}
                  </div>
                  <CardDescription className="mt-1 text-sm">
                    {post.description}
                  </CardDescription>
                </CardHeader>
              </Link>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-8 text-center">
        <Button variant="outline" render={<Link to="/blog" />}>
          ← 返回博客
        </Button>
      </div>
    </div>
  )
}
