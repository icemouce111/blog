import { AiDailyArchiveList, AiDailyLatestIssue } from '@/components/ai-daily/AiDailyIssueList'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiTrendInsights } from '@/components/ai-daily/AiTrendInsights'
import { AiOpportunityRadar } from '@/components/ai-daily/AiOpportunityRadar'
import { GithubDailyDigest } from '@/components/ai-daily/GithubDailyDigest'
import { ReadingLayout } from '@/components/reading/ReadingLayout'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import trendSeed from '@/data/ai-trends.json'
import { getAiDailyPosts } from '@/lib/ai-daily'
import { parseAiTrendData } from '@/lib/ai-trends'
import { getGithubDailyPosts } from '@/lib/github-daily'
import { getGithubDigestLabel } from '@/lib/github-daily-digest'
import { getActiveAiOpportunities } from '@/lib/ai-opportunities'
import type { ReadingSection } from '@/lib/reading-navigation'

export function AiDailyPage() {
  const posts = getAiDailyPosts()
  const githubPost = getGithubDailyPosts()[0]
  const opportunityCount = getActiveAiOpportunities().length
  const openSourceCount = Math.min(
    3,
    githubPost?.highlights.length || githubPost?.repos.length || 0,
  )
  const openSourceLabel = githubPost ? getGithubDigestLabel(githubPost) : undefined
  const navigationSections: ReadingSection[] = [
    { id: 'latest-issue-heading', title: '今日主线' },
    { id: 'creator-opportunities', title: 'AI 创作者机会' },
    ...(githubPost ? [{ id: 'github-picks', title: 'GitHub 每日新增 Star 排行' }] : []),
    ...(parseAiTrendData(trendSeed).windows.length
      ? [{ id: 'trend-heading', title: 'AI 应用趋势洞察' }]
      : []),
    ...(posts.length > 1 ? [{ id: 'daily-archive-heading', title: '往期简报' }] : []),
  ]

  return (
    <div className="ai-daily-shell">
      <PageContainer size="wide" className="ai-daily-paper ai-daily-index">
        <AiDailyMasthead heading date={posts[0]?.date} issueId={posts[0]?.issueId} />
        {posts.length > 0 ? (
          <ReadingLayout sections={navigationSections}>
            <div className="ai-daily-archive-layout">
              <AiDailyLatestIssue
                latest={posts[0]}
                openSourceCount={openSourceCount}
                openSourceLabel={openSourceLabel}
                opportunityCount={opportunityCount}
              />
              <AiOpportunityRadar />
              {githubPost && <GithubDailyDigest post={githubPost} />}
              <AiTrendInsights />
              <AiDailyArchiveList archive={posts.slice(1)} />
            </div>
          </ReadingLayout>
        ) : (
          <section className="ai-daily-empty">
            <p className="ai-daily-eyebrow">ARCHIVE</p>
            <h2 className="ai-daily-serif">编辑部正在整理今天的信号</h2>
          </section>
        )}
      </PageContainer>
    </div>
  )
}
