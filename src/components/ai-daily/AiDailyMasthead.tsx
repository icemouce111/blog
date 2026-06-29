interface AiDailyMastheadProps {
  date?: string
  issueId?: string
}

export function AiDailyMasthead({ date, issueId }: AiDailyMastheadProps) {
  return (
    <header className="ai-daily-masthead">
      <div>
        <p className="ai-daily-eyebrow">DAILY AI INTELLIGENCE</p>
        <p className="ai-daily-brand ai-daily-serif">AI 日报</p>
      </div>
      <div className="ai-daily-masthead-meta">
        {date ? <time>{date}</time> : <span>每日更新</span>}
        {issueId && <span>第 {issueId} 期</span>}
      </div>
    </header>
  )
}
