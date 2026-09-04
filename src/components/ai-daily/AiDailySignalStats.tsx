interface AiDailySignalStatsProps {
  signals: number
  openSource: number
  openSourceLabel?: string
  opportunities: number
}

export function AiDailySignalStats({
  signals,
  openSource,
  openSourceLabel = '开源精选',
  opportunities,
}: AiDailySignalStatsProps) {
  return (
    <dl className="ai-daily-signal-stats" aria-label="本期情报概览">
      <div>
        <dt>今日信号</dt>
        <dd><strong>{signals}</strong><span>条</span></dd>
      </div>
      <div>
        <dt>{openSourceLabel}</dt>
        <dd><strong>{openSource}</strong><span>个</span></dd>
      </div>
      <div>
        <dt>可行动机会</dt>
        <dd><strong>{opportunities}</strong><span>项</span></dd>
      </div>
    </dl>
  )
}
