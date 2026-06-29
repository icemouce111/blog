import {
  AiDailyArchiveList,
  AiDailyLatestIssue,
} from '@/components/ai-daily/AiDailyIssueList'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiTrendInsights } from '@/components/ai-daily/AiTrendInsights'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import { getAiDailyPosts } from '@/lib/ai-daily'

export function AiDailyPage() {
  const posts = getAiDailyPosts()

  return (
    <div className="ai-daily-shell">
      <PageContainer size="wide" className="ai-daily-paper">
        <AiDailyMasthead />
        {posts.length > 0 ? (
          <div className="ai-daily-archive-layout">
            <AiDailyLatestIssue latest={posts[0]} />
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
