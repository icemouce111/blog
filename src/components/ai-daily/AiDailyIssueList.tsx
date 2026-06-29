import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import type { AiDailyMeta } from '@/lib/ai-daily'

interface AiDailyLatestIssueProps {
  latest: AiDailyMeta
}

interface AiDailyArchiveListProps {
  archive: AiDailyMeta[]
}

export function AiDailyLatestIssue({ latest }: AiDailyLatestIssueProps) {
  return (
    <article className="ai-daily-featured" aria-labelledby="latest-issue-heading">
      <div className="ai-daily-section-label">
        <span>最新一期</span>
        <time dateTime={latest.dateISO}>{latest.date}</time>
      </div>
      <p className="ai-daily-original-title">{latest.title}</p>
      <h1 id="latest-issue-heading" className="ai-daily-serif">
        <Link to={`/ai-daily/${latest.slug}`}>{latest.leadTitle}</Link>
      </h1>
      {latest.leadSummary && (
        <div className="ai-daily-featured-summary">
          <ReactMarkdown>{latest.leadSummary}</ReactMarkdown>
        </div>
      )}
      <div className="ai-daily-meta-line" aria-label="本期信息">
        <span>{latest.storyCount} 条信号</span>
        <span>{latest.sourceCount} 个来源</span>
        <span>约 {latest.readingMinutes} 分钟</span>
      </div>
      <Link className="ai-daily-read-link" to={`/ai-daily/${latest.slug}`}>
        阅读本期 <span aria-hidden="true">→</span>
      </Link>
    </article>
  )
}

export function AiDailyArchiveList({ archive }: AiDailyArchiveListProps) {
  if (archive.length === 0) return null

  return (
    <section className="ai-daily-archive" aria-labelledby="daily-archive-heading">
      <div className="ai-daily-section-label">
        <h2 id="daily-archive-heading">往期简报</h2>
        <span>{archive.length} 期</span>
      </div>
      <ol className="ai-daily-archive-list">
        {archive.map((post) => (
          <li key={post.slug}>
            <Link to={`/ai-daily/${post.slug}`}>
              <time dateTime={post.dateISO}>{post.dateISO.slice(5).replace('-', '.')}</time>
              <span className="ai-daily-archive-copy">
                <span className="ai-daily-archive-title ai-daily-serif">{post.leadTitle}</span>
                <span className="ai-daily-archive-note">
                  {post.isSignalArchive ? '原始信号归档' : `${post.storyCount} 条编辑信号`}
                </span>
              </span>
              <span className="ai-daily-archive-arrow" aria-hidden="true">↗</span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  )
}
