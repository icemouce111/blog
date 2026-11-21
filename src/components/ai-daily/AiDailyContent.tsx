import type { ReactNode } from 'react'
import { MarkdownContent } from '@/components/reading/MarkdownContent'
import { Disclosure } from '@/components/ui/disclosure'
import type { AiDailyPost } from '@/lib/ai-daily'
import type { AiDailySection } from '@/lib/ai-daily-parser'
import { AiDailySignalStats } from './AiDailySignalStats'

interface AiDailyContentProps {
  post: AiDailyPost
  sections?: AiDailySection[]
  afterSections?: ReactNode
}

export function AiDailyContent({
  post,
  sections = post.parsed.sections,
  afterSections,
}: AiDailyContentProps) {
  const { parsed } = post
  const leadTitle = parsed.leadStory?.title || post.leadTitle
  const leadSummary = parsed.leadStory?.summaryMarkdown || post.leadSummary

  return (
    <div className="ai-daily-content">
      <div className="ai-daily-briefing-bar">
        <span>行动简报 / {post.date}</span>
        <span className="ai-daily-format-label">{post.isSignalArchive ? '来源速览' : '编辑简报'}</span>
      </div>
      <header className="ai-daily-story-header">
        <p className="ai-daily-featured-kicker">
          <span /> {post.isSignalArchive ? '本期资讯' : '今日主线'}
        </p>
        <h1 id="daily-issue-heading" className="ai-daily-serif">{leadTitle}</h1>
        {leadSummary && (
          <div className="ai-daily-standfirst">
            <MarkdownContent sections={[]}>{leadSummary}</MarkdownContent>
          </div>
        )}
        <div className="ai-daily-lead-meta">
          {parsed.leadStory?.confidence && <span>{parsed.leadStory.confidence}</span>}
          {parsed.leadStory?.sourceUrl && (
            <a href={parsed.leadStory.sourceUrl} target="_blank" rel="noreferrer">
              查看原始来源 <span aria-hidden="true">↗</span>
            </a>
          )}
        </div>
      </header>

      <AiDailySignalStats
        signals={post.storyCount}
        sources={post.sourceCount}
        readingMinutes={post.readingMinutes}
        isSignalArchive={post.isSignalArchive}
      />

      {sections.map((section) => (
        <Disclosure
          open
          className="ai-daily-content-section ai-daily-foldable"
          id={section.id}
          key={section.id}
          aria-labelledby={`${section.id}-heading`}
        >
          <summary className="ai-daily-content-heading">
            <span>{section.number}</span>
            <h2 id={`${section.id}-heading`} className="ai-daily-serif">
              {section.title}
            </h2>
          </summary>
          {section.markdown && (
            <div className="ai-daily-markdown">
              <MarkdownContent sections={[]}>{section.markdown}</MarkdownContent>
            </div>
          )}
        </Disclosure>
      ))}

      {parsed.fallbackMarkdown && (
        <Disclosure open className="ai-daily-content-section ai-daily-foldable">
          <summary className="ai-daily-content-heading"><h2>本期内容</h2></summary>
          <div className="ai-daily-markdown">
            <MarkdownContent sections={[]}>{parsed.fallbackMarkdown}</MarkdownContent>
          </div>
        </Disclosure>
      )}

      {afterSections}

      {parsed.footer && (
        <footer className="ai-daily-issue-footer">{parsed.footer.replaceAll('*', '')}</footer>
      )}
    </div>
  )
}
