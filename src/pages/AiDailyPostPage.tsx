import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AiDailyContent } from '@/components/ai-daily/AiDailyContent'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiDailySupplements } from '@/components/ai-daily/AiDailySupplements'
import { ReadingLayout } from '@/components/reading/ReadingLayout'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import { getAiDailyPost, getAiDailyPosts } from '@/lib/ai-daily'
import { getAiDailyReadingSections } from '@/lib/ai-daily-parser'
import { getGithubDailyForDate } from '@/lib/github-daily'

export function AiDailyPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = useMemo(() => (slug ? getAiDailyPost(slug) : null), [slug])
  const githubPost = post ? getGithubDailyForDate(post.dateISO) : null
  const showOpportunities = Boolean(post && getAiDailyPosts()[0]?.slug === post.slug)
  const contentSections = useMemo(() => {
    if (!post) return []
    return getAiDailyReadingSections(post.parsed).filter((section) => section.markdown.trim())
  }, [post])
  const navigationSections = useMemo(() => {
    return [
      { id: 'daily-issue-heading', title: '本期资讯' },
      ...contentSections,
      ...(githubPost || showOpportunities ? [{ id: 'daily-extras', title: '工具与机会' }] : []),
      ...(githubPost ? [{ id: 'github-picks', title: 'GitHub 开源项目', level: 3 as const }] : []),
      ...(showOpportunities ? [{ id: 'creator-opportunities', title: 'AI 创作者机会', level: 3 as const }] : []),
    ]
  }, [contentSections, githubPost, showOpportunities])

  if (!post) {
    return (
      <div className="ai-daily-shell">
        <PageContainer size="narrow" className="ai-daily-paper ai-daily-empty">
          <p className="ai-daily-eyebrow">404 / NOT FOUND</p>
          <h1 className="ai-daily-serif">这期日报不在档案中</h1>
          <Link className="ai-daily-back" to="/ai-daily">
            ← 返回情报归档
          </Link>
        </PageContainer>
      </div>
    )
  }

  return (
    <div className="ai-daily-shell">
      <PageContainer size="wide" className="ai-daily-paper">
        <Link className="ai-daily-back" to="/ai-daily">
          ← 返回情报归档
        </Link>
        <AiDailyMasthead date={post.date} issueId={post.issueId} />
        <ReadingLayout
          sections={navigationSections}
          directoryFooter={
            <>
              <p>
                {post.storyCount} 条{post.isSignalArchive ? '来源记录' : '解读'} · {post.readingMinutes} 分钟阅读
              </p>
              <nav aria-label="相邻日报">
                {post.newerSlug && <Link to={`/ai-daily/${post.newerSlug}`}>← 更新一期</Link>}
                {post.olderSlug && <Link to={`/ai-daily/${post.olderSlug}`}>更早一期 →</Link>}
              </nav>
            </>
          }
        >
          <AiDailyContent
            afterSections={
              <AiDailySupplements githubPost={githubPost} showOpportunities={showOpportunities} fullOpportunities />
            }
            post={post}
            sections={contentSections}
          />
        </ReadingLayout>
      </PageContainer>
    </div>
  )
}
