import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MarkdownContent } from '@/components/reading/MarkdownContent'
import type { AiDailyMeta, AiDailyPost } from '@/lib/ai-daily'
import type { AiDailySection } from '@/lib/ai-daily-parser'
import { AiDailySignalStats } from './AiDailySignalStats'

interface AiDailyLatestIssueProps {
  latest: AiDailyPost
  sections: AiDailySection[]
}

interface AiDailyArchiveListProps {
  archive: AiDailyMeta[]
}

export function AiDailyLatestIssue({
  latest,
  sections,
}: AiDailyLatestIssueProps) {
  const previews = sections.filter((section) => section.markdown.trim()).slice(0, 4)
  return (
    <section className="ai-daily-latest" aria-labelledby="latest-issue-heading">
      <div className="ai-daily-briefing-bar">
        <span>最新一期 / {latest.dateISO}</span>
        <div className="ai-daily-briefing-links">
          <span className="ai-daily-format-label">{latest.isSignalArchive ? '来源速览' : '编辑简报'}</span>
          <Link to={`/ai-daily/${latest.slug}`}>全文 ↗</Link>
        </div>
      </div>
      <article className="ai-daily-featured">
        <div className="ai-daily-featured-kicker">
          <span /> {latest.isSignalArchive ? '本期资讯' : '今日主线'}
        </div>
        <h2 id="latest-issue-heading" className="ai-daily-serif">
          <Link to={`/ai-daily/${latest.slug}`}>{latest.leadTitle}</Link>
        </h2>
        {latest.leadSummary && (
          <div className="ai-daily-featured-summary">
            <MarkdownContent sections={[]}>{latest.leadSummary}</MarkdownContent>
          </div>
        )}
      </article>
      <AiDailySignalStats
        signals={latest.storyCount}
        sources={latest.sourceCount}
        readingMinutes={latest.readingMinutes}
        isSignalArchive={latest.isSignalArchive}
      />
      <div className="ai-daily-news-preview">
        {previews.map((section, index) => {
          const previewMarkdown = section.markdown.replace(
            /^(\s*(?:[-*+]|\d+\.)\s+\*\*[^*\n]+\*\*)[：:][ \t]*/gm,
            '$1\n\n    ',
          )
          return (
            <section id={section.id} key={section.id} aria-labelledby={`${section.id}-preview-heading`}>
              <header className="ai-daily-news-heading">
                <span>{String(index + 1).padStart(2, '0')}</span>
                <h3 id={`${section.id}-preview-heading`}>{section.title}</h3>
                <Link to={`/ai-daily/${latest.slug}#${encodeURIComponent(section.id)}`}>本期全文 ↗</Link>
              </header>
              <MarkdownContent sections={[]}>{previewMarkdown}</MarkdownContent>
            </section>
          )
        })}
        {latest.parsed.fallbackMarkdown && (
          <MarkdownContent sections={[]}>{latest.parsed.fallbackMarkdown}</MarkdownContent>
        )}
      </div>
      <Link className="ai-daily-all-stories" to={`/ai-daily/${latest.slug}`}>
        查看本期全部内容 <span aria-hidden="true">→</span>
      </Link>
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
                  {post.isSignalArchive ? `来源速览 · ${post.storyCount} 条记录` : `${post.storyCount} 条编辑信号`}
                </span>
              </span>
              <span className="ai-daily-archive-arrow" aria-hidden="true">
                ↗
              </span>
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
