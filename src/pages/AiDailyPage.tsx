import {
  AiDailyArchiveList,
  AiDailyLatestIssue,
} from '@/components/ai-daily/AiDailyIssueList'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiTrendInsights } from '@/components/ai-daily/AiTrendInsights'
import { AiOpportunityRadar } from '@/components/ai-daily/AiOpportunityRadar'
import { GithubDailyDigest } from '@/components/ai-daily/GithubDailyDigest'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import { getAiDailyPosts } from '@/lib/ai-daily'
import { getGithubDailyPosts } from '@/lib/github-daily'
import { getActiveAiOpportunities } from '@/lib/ai-opportunities'

export function AiDailyPage() {
  const posts = getAiDailyPosts()
  const githubPost = getGithubDailyPosts()[0]
  const opportunityCount = getActiveAiOpportunities().length
  const openSourceCount = Math.min(3, githubPost?.highlights.length || githubPost?.repos.length || 0)

  return (
    <div className="ai-daily-shell">
      <PageContainer size="wide" className="ai-daily-paper">
        <AiDailyMasthead date={posts[0]?.date} issueId={posts[0]?.issueId} />
        {posts.length > 0 ? (
          <div className="ai-daily-archive-layout">
            <AiDailyLatestIssue
              latest={posts[0]}
              openSourceCount={openSourceCount}
              opportunityCount={opportunityCount}
            />
            <AiOpportunityRadar />
            {githubPost && <GithubDailyDigest post={githubPost} />}
            <AiTrendInsights />
            <AiDailyArchiveList archive={posts.slice(1)} />
          </div>
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
