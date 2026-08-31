import { Link } from 'react-router-dom'
import { Flame, Star, Sparkles, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageContainer } from '@/components/layout/PageContainer'
import { getGithubDailyPosts, type GithubDailyPost } from '@/lib/github-daily'

function PostSummary({ post }: { post: GithubDailyPost }) {
  const topRepos = post.repos.slice(0, 3)
  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-lg">{post.dateDisplay}</CardTitle>
          {post.mode === 'analyzed' ? (
            <Badge variant="secondary" className="shrink-0 gap-1">
              <Sparkles className="h-3 w-3" /> AI 解读
            </Badge>
          ) : (
            <Badge variant="outline" className="shrink-0">
              原始榜单
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{post.intro}</p>
        <div className="space-y-1 text-sm">
          {topRepos.map((repo) => (
            <div key={repo.fullName} className="flex items-center gap-2 text-muted-foreground">
              <span className="font-mono text-xs w-4">{repo.rank}</span>
              <span className="font-medium text-foreground">{repo.fullName}</span>
              {repo.starsToday !== null && (
                <span className="text-xs">+{repo.starsToday}</span>
              )}
            </div>
          ))}
        </div>
        <Link
          to={`/github/${post.slug}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-primary mt-4 hover:underline"
        >
          查看本期 <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </CardContent>
    </Card>
  )
}

export function GithubPage() {
  const posts = getGithubDailyPosts()

  return (
    <PageContainer>
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2 flex items-center gap-2">
          <Flame className="h-7 w-7 text-orange-500" /> GitHub 榜单
        </h1>
        <p className="text-muted-foreground">
          每日追踪 GitHub Trending 热门项目，AI 帮你解读每个项目是干啥的、对你有什么用
        </p>
      </div>

      {posts.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          第一期榜单正在路上...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {posts.map((post) => (
            <PostSummary key={post.slug} post={post} />
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground mt-8 flex items-center gap-1">
        <Star className="h-3 w-3" />
        数据来自 GitHub Trending（每日榜），由 AI 生成的解读仅供参考
      </p>
    </PageContainer>
  )
}
