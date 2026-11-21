import { AiDailyArchiveList, AiDailyLatestIssue } from '@/components/ai-daily/AiDailyIssueList'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiDailySupplements } from '@/components/ai-daily/AiDailySupplements'
import { ReadingLayout } from '@/components/reading/ReadingLayout'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import trendSeed from '@/data/ai-trends.json'
import { getAiDailyPost, getAiDailyPosts } from '@/lib/ai-daily'
import { getAiDailyReadingSections } from '@/lib/ai-daily-parser'
import { parseAiTrendData } from '@/lib/ai-trends'
import { getGithubDailyPosts } from '@/lib/github-daily'
import type { ReadingSection } from '@/lib/reading-navigation'

export function AiDailyPage() {
  const posts = getAiDailyPosts()
  const latest = posts[0] ? getAiDailyPost(posts[0].slug) : null
  const githubPost = getGithubDailyPosts()[0]
  const sections = latest ? getAiDailyReadingSections(latest.parsed) : []
  const previews = sections.filter((section) => section.markdown.trim()).slice(0, 4)
  const navigationSections: ReadingSection[] = [
    { id: 'latest-issue-heading', title: '本期资讯' },
    ...previews.map((section) => ({ id: section.id, title: section.title, level: 3 as const })),
    { id: 'daily-extras', title: '工具与机会' },
    ...(githubPost ? [{ id: 'github-picks', title: 'GitHub 开源项目', level: 3 as const }] : []),
    { id: 'creator-opportunities', title: 'AI 创作者机会', level: 3 },
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
              {latest && <AiDailyLatestIssue latest={latest} sections={sections} />}
              <AiDailySupplements githubPost={githubPost} showTrends />
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
