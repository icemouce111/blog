import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ComponentPropsWithoutRef, ReactNode } from 'react'
import type { AiDailyPost } from '@/lib/ai-daily'
import type { AiDailySection } from '@/lib/ai-daily-parser'
import { AiDailySignalStats } from './AiDailySignalStats'

interface AiDailyContentProps {
  post: AiDailyPost
  sections?: AiDailySection[]
  beforeSections?: ReactNode
  afterSections?: ReactNode
  openSourceCount?: number
  openSourceLabel?: string
  opportunityCount?: number
}

function ExternalLink({ href, children, ...props }: ComponentPropsWithoutRef<'a'>) {
  const external = href?.startsWith('http')
  return (
    <a
      href={href}
      {...props}
      {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}
    >
      {children}
    </a>
  )
}

const markdownComponents = {
  a: ExternalLink,
}

export function AiDailyContent({
  post,
  sections = post.parsed.sections,
  beforeSections,
  afterSections,
  openSourceCount = 0,
  openSourceLabel,
  opportunityCount = 0,
}: AiDailyContentProps) {
  const { parsed } = post
  const leadTitle = parsed.leadStory?.title || post.leadTitle
  const leadSummary = parsed.leadStory?.summaryMarkdown || post.leadSummary

  return (
    <div className="ai-daily-content">
      <div className="ai-daily-briefing-bar">
        <span>MORNING BRIEFING / ISSUE {post.issueId.slice(-4)}</span>
        <strong>预计阅读 {post.readingMinutes} 分钟</strong>
      </div>
      <header className="ai-daily-story-header">
        <p className="ai-daily-featured-kicker"><span /> TODAY&apos;S DEFINING SHIFT</p>
        <h1 className="ai-daily-serif">{leadTitle}</h1>
        {leadSummary && (
          <div className="ai-daily-standfirst">
            <ReactMarkdown components={markdownComponents}>
              {leadSummary}
            </ReactMarkdown>
          </div>
        )}
        <div className="ai-daily-featured-orbit" aria-hidden="true"><span>AI</span></div>
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
        openSource={openSourceCount}
        openSourceLabel={openSourceLabel}
        opportunities={opportunityCount}
      />

      {beforeSections}

      {sections.map((section) => (
        <section
          className="ai-daily-content-section"
          id={section.id}
          key={section.id}
          aria-labelledby={`${section.id}-heading`}
        >
          <div className="ai-daily-content-heading">
            <span>{section.number}</span>
            <h2 id={`${section.id}-heading`} className="ai-daily-serif">{section.title}</h2>
          </div>
          {section.markdown && (
            <div className="ai-daily-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {section.markdown}
              </ReactMarkdown>
            </div>
          )}
        </section>
      ))}

      {parsed.fallbackMarkdown && (
        <section className="ai-daily-content-section">
          <div className="ai-daily-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {parsed.fallbackMarkdown}
            </ReactMarkdown>
          </div>
        </section>
      )}

      {afterSections}

      {parsed.footer && <footer className="ai-daily-issue-footer">{parsed.footer.replaceAll('*', '')}</footer>}
    </div>
  )
}
