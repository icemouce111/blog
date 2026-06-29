import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ComponentPropsWithoutRef } from 'react'
import type { AiDailyPost } from '@/lib/ai-daily'

interface AiDailyContentProps {
  post: AiDailyPost
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

export function AiDailyContent({ post }: AiDailyContentProps) {
  const { parsed } = post
  const leadTitle = parsed.leadStory?.title || post.leadTitle

  return (
    <div className="ai-daily-content">
      <header className="ai-daily-story-header">
        <p className="ai-daily-original-title">{post.title}</p>
        <h1 className="ai-daily-serif">{leadTitle}</h1>
        {parsed.leadStory?.summaryMarkdown && (
          <div className="ai-daily-standfirst">
            <ReactMarkdown components={markdownComponents}>
              {parsed.leadStory.summaryMarkdown}
            </ReactMarkdown>
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

      {parsed.sections.map((section) => (
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

      {parsed.footer && <footer className="ai-daily-issue-footer">{parsed.footer.replaceAll('*', '')}</footer>}
    </div>
  )
}
