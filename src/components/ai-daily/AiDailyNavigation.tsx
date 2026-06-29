import { Link } from 'react-router-dom'
import type { AiDailyPost } from '@/lib/ai-daily'
import type { ParsedAiDailyContent } from '@/lib/ai-daily-parser'

interface MobileNavigationProps {
  parsed: ParsedAiDailyContent
}

interface DesktopNavigationProps {
  post: AiDailyPost
  activeSection: string
  onSectionClick: (id: string) => void
}

export function AiDailyMobileNavigation({ parsed }: MobileNavigationProps) {
  if (!parsed.sections.length) return null

  return (
    <nav className="ai-daily-mobile-nav" aria-label="本期章节">
      {parsed.sections.map((section) => (
        <a key={section.id} href={`#${section.id}`}>
          <span>{section.number}</span>
          {section.title}
        </a>
      ))}
    </nav>
  )
}

export function AiDailyDesktopNavigation({
  post,
  activeSection,
  onSectionClick,
}: DesktopNavigationProps) {
  return (
    <aside className="ai-daily-desktop-nav">
      <div className="ai-daily-nav-sticky">
        {post.parsed.sections.length > 0 && (
          <nav aria-label="本期目录">
            <p className="ai-daily-eyebrow">本期目录</p>
            <ol>
              {post.parsed.sections.map((section) => (
                <li key={section.id}>
                  <a
                    aria-current={activeSection === section.id ? 'location' : undefined}
                    href={`#${section.id}`}
                    onClick={(event) => {
                      event.preventDefault()
                      onSectionClick(section.id)
                    }}
                  >
                    <span>{section.number}</span>
                    {section.title}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
        )}

        <dl className="ai-daily-issue-stats">
          <div><dt>信号</dt><dd>{post.storyCount}</dd></div>
          <div><dt>来源</dt><dd>{post.sourceCount}</dd></div>
          <div><dt>阅读</dt><dd>{post.readingMinutes} 分钟</dd></div>
        </dl>

        <nav className="ai-daily-adjacent" aria-label="相邻日报">
          {post.newerSlug && <Link to={`/ai-daily/${post.newerSlug}`}>← 更新一期</Link>}
          {post.olderSlug && <Link to={`/ai-daily/${post.olderSlug}`}>更早一期 →</Link>}
        </nav>
      </div>
    </aside>
  )
}
