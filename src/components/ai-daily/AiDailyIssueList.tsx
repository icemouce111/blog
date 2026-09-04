import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import type { AiDailyMeta } from '@/lib/ai-daily'
import { AiDailySignalStats } from './AiDailySignalStats'

interface AiDailyLatestIssueProps {
  latest: AiDailyMeta
  openSourceCount: number
  openSourceLabel?: string
  opportunityCount: number
}

interface AiDailyArchiveListProps {
  archive: AiDailyMeta[]
}

export function AiDailyLatestIssue({
  latest,
  openSourceCount,
  openSourceLabel,
  opportunityCount,
}: AiDailyLatestIssueProps) {
  return (
    <section className="ai-daily-latest" aria-labelledby="latest-issue-heading">
      <div className="ai-daily-briefing-bar">
        <span>MORNING BRIEFING / ISSUE {latest.issueId.slice(-4)}</span>
        <strong>预计阅读 {latest.readingMinutes} 分钟</strong>
      </div>
      <article className="ai-daily-featured">
        <div className="ai-daily-featured-kicker"><span /> TODAY&apos;S DEFINING SHIFT</div>
        <h1 id="latest-issue-heading" className="ai-daily-serif">
          <Link to={`/ai-daily/${latest.slug}`}>{latest.leadTitle}</Link>
        </h1>
        {latest.leadSummary && (
          <div className="ai-daily-featured-summary">
            <ReactMarkdown>{latest.leadSummary}</ReactMarkdown>
          </div>
        )}
        <div className="ai-daily-featured-orbit" aria-hidden="true"><span>AI</span></div>
        <Link className="ai-daily-read-link" to={`/ai-daily/${latest.slug}`}>
          <span aria-hidden="true">→</span> 阅读本期行动情报
        </Link>
      </article>
      <AiDailySignalStats
        signals={latest.storyCount}
        openSource={openSourceCount}
        openSourceLabel={openSourceLabel}
        opportunities={opportunityCount}
      />
    </section>
  )
}

export function AiDailyArchiveList({ archive }: AiDailyArchiveListProps) {
  const [expanded, setExpanded] = useState(false)
  if (archive.length === 0) return null

  const visibleArchive = expanded ? archive : archive.slice(0, 8)

  return (
    <section className="ai-daily-archive" aria-labelledby="daily-archive-heading">
      <div className="ai-daily-section-label">
        <h2 id="daily-archive-heading">往期简报</h2>
        <span>{archive.length} 期</span>
      </div>
      <ol className="ai-daily-archive-list">
        {visibleArchive.map((post) => (
          <li key={post.slug}>
            <Link to={`/ai-daily/${post.slug}`}>
              <time dateTime={post.dateISO}>{post.dateISO.slice(5).replace('-', '.')}</time>
              <span className="ai-daily-archive-copy">
                <span className="ai-daily-archive-title ai-daily-serif">{post.leadTitle}</span>
                <span className="ai-daily-archive-note">
                  {post.isSignalArchive ? '来源速览' : `${post.storyCount} 条编辑信号`}
                </span>
              </span>
              <span className="ai-daily-archive-arrow" aria-hidden="true">↗</span>
            </Link>
          </li>
        ))}
      </ol>
      {archive.length > 8 && (
        <button
          aria-expanded={expanded}
          className="ai-daily-archive-toggle"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? '收起往期' : `查看全部 ${archive.length} 期`}
        </button>
      )}
    </section>
  )
}
