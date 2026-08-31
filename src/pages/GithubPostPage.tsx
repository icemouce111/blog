import { Link, useParams } from 'react-router-dom'
import { Flame, Sparkles, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { PageContainer } from '@/components/layout/PageContainer'
import {
  formatStars,
  getGithubDailyPost,
} from '@/lib/github-daily'

export function GithubPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = slug ? getGithubDailyPost(slug) : null

  if (!post) {
    return (
      <PageContainer>
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">这期榜单不在档案中</p>
          <Link to="/github" className="text-primary hover:underline">
            ← 返回榜单归档
          </Link>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <Link to="/github" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← 返回榜单归档
      </Link>

      <div className="mt-4 mb-8">
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Flame className="h-7 w-7 text-orange-500" /> GitHub 每日榜单
          </h1>
          {post.mode === 'analyzed' ? (
            <Badge variant="secondary" className="gap-1">
              <Sparkles className="h-3 w-3" /> AI 解读
            </Badge>
          ) : (
            <Badge variant="outline">原始榜单</Badge>
          )}
        </div>
        <p className="text-muted-foreground">
          {post.dateDisplay} · {post.repos.length} 个热门项目
        </p>
      </div>

      <Card className="mb-8 border-primary/20 bg-primary/5">
        <CardContent className="pt-6">
          <p className="text-sm leading-relaxed">{post.intro}</p>
        </CardContent>
      </Card>

      {post.highlights.length > 0 && (
        <section className="mb-10" aria-labelledby="highlights-heading">
          <h2 id="highlights-heading" className="text-xl font-bold mb-1 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-500" /> 精选榜单
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            AI 从今日榜中挑出的最值得关注项目
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {post.highlights.map((highlight) => {
              const repo = post.repos.find((item) => item.fullName === highlight.repo)
              return (
                <Card key={highlight.repo} className="flex flex-col">
                  <CardHeader>
                    <CardTitle className="text-base">{highlight.title}</CardTitle>
                    <CardDescription className="flex items-center gap-2">
                      <a
                        href={repo?.url ?? `https://github.com/${highlight.repo}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-xs font-medium text-primary hover:underline inline-flex items-center gap-1"
                      >
                        {highlight.repo} <ExternalLink className="h-3 w-3" />
                      </a>
                      {repo?.language && (
                        <Badge variant="outline" className="text-xs">
                          {repo.language}
                        </Badge>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1 space-y-3 text-sm leading-relaxed">
                    <p>
                      <span className="font-medium">为什么值得关注：</span>
                      {highlight.why}
                    </p>
                    <p>
                      <span className="font-medium">对你的价值：</span>
                      {highlight.value}
                    </p>
                    <p>
                      <span className="font-medium">怎么上手：</span>
                      {highlight.how}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </section>
      )}

      <section aria-labelledby="board-heading">
        <h2 id="board-heading" className="text-xl font-bold mb-4">热门榜单</h2>
        <div className="space-y-3">
          {post.repos.map((repo) => (
            <Card key={repo.fullName}>
              <CardContent className="pt-5">
                <div className="flex items-start gap-3">
                  <span className="font-mono text-lg font-bold text-muted-foreground/60 w-7 shrink-0 text-right">
                    {repo.rank}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <a
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold hover:text-primary transition-colors"
                      >
                        {repo.fullName}
                      </a>
                      {repo.language && (
                        <Badge variant="outline" className="text-xs">
                          {repo.language}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        ★ {formatStars(repo.stars)}
                        {repo.starsToday !== null && (
                          <span className="text-orange-500 ml-1">+{repo.starsToday} 今日</span>
                        )}
                      </span>
                    </div>
                    <p className="text-sm text-foreground/90 mb-1">{repo.what}</p>
                    {repo.help && (
                      <p className="text-sm text-muted-foreground">
                        <span className="font-medium">对你：</span>
                        {repo.help}
                      </p>
                    )}
                    {repo.description && !repo.what && (
                      <p className="text-sm text-muted-foreground">{repo.description}</p>
                    )}
                    {repo.topics.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {repo.topics.slice(0, 4).map((topic) => (
                          <Badge key={topic} variant="secondary" className="text-xs">
                            {topic}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <nav className="flex items-center justify-between mt-10 pt-6 border-t" aria-label="期数导航">
        {post.newerSlug ? (
          <Link
            to={`/github/${post.newerSlug}`}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" /> 更新一期
          </Link>
        ) : (
          <span />
        )}
        {post.olderSlug ? (
          <Link
            to={`/github/${post.olderSlug}`}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            更早一期 <ChevronRight className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>

      <p className="text-xs text-muted-foreground mt-6">
        生成于 {post.generatedAt} CST · 数据来自 GitHub Trending，解读由 AI 生成、仅供参考
      </p>
    </PageContainer>
  )
}
