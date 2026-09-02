interface AiDailyMastheadProps {
  date?: string
  issueId?: string
}

export function AiDailyMasthead({ date, issueId }: AiDailyMastheadProps) {
  return (
    <header className="ai-daily-masthead">
      <div className="ai-daily-identity">
        <span className="ai-daily-mark" aria-hidden="true"><Sparkles /></span>
        <div>
          <p className="ai-daily-brand">AI 行动情报站</p>
          <p className="ai-daily-brand-note">FILTER · EXPLAIN · ACT</p>
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
