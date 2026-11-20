interface AiDailyMastheadProps {
  heading?: boolean
  date?: string
  issueId?: string
}

export function AiDailyMasthead({ date, issueId, heading }: AiDailyMastheadProps) {
  return (
    <header className="ai-daily-masthead">
      <div className="ai-daily-identity">
        <span className="ai-daily-mark" aria-hidden="true">
          <Sparkles />
        </span>
        <div>
          {heading ? (
            <h1 className="ai-daily-brand">AI 行动情报站</h1>
          ) : (
            <p className="ai-daily-brand">AI 行动情报站</p>
          )}
          <p className="ai-daily-brand-note">筛选变化 · 理解价值 · 开始行动</p>
        </div>
      </div>
      <div className="ai-daily-masthead-meta">
        {date ? <time>{date}</time> : <span>每日更新</span>}
        {issueId && <span>ISSUE {issueId.slice(-4)}</span>}
      </div>
    </header>
  )
}
import { Sparkles } from 'lucide-react'
