interface AiDailySignalStatsProps {
  signals: number
  sources: number
  readingMinutes: number
  isSignalArchive?: boolean
}

export function AiDailySignalStats({
  signals,
  sources,
  readingMinutes,
  isSignalArchive = false,
}: AiDailySignalStatsProps) {
  return (
    <dl className="ai-daily-signal-stats" aria-label="本期情报概览">
      <div>
        <dt>{isSignalArchive ? '收录条目' : '本期解读'}</dt>
        <dd><strong>{signals}</strong><span>条</span></dd>
      </div>
      <div>
        <dt>来源链接</dt>
        <dd><strong>{sources}</strong><span>个</span></dd>
      </div>
      <div>
        <dt>预计阅读</dt>
        <dd><strong>{readingMinutes}</strong><span>分钟</span></dd>
      </div>
    </dl>
  )
}
