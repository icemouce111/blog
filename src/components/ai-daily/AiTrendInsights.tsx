import { useId, useMemo, useState } from 'react'
import trendSeed from '@/data/ai-trends.json'
import {
  parseAiTrendData,
  type TrendSnapshot,
  type TrendWindow,
} from '@/lib/ai-trends'

const labels: Record<TrendWindow, string> = {
  week: '近周',
  month: '近月',
  year: '近年',
}

function formatShortDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    timeZone: 'Asia/Shanghai',
  }).format(new Date(`${value}T00:00:00+08:00`))
}

function sourceCount(snapshot: TrendSnapshot) {
  return new Set(
    snapshot.insights.flatMap((insight) => insight.sources.map((source) => source.url))
  ).size
}

export function AiTrendInsights() {
  const tabsId = useId()
  const trendData = useMemo(() => parseAiTrendData(trendSeed), [])
  const [activeWindow, setActiveWindow] = useState<TrendWindow>('week')
  const active = trendData.windows.find((item) => item.window === activeWindow)

  if (!active) return null

  return (
    <aside className="ai-trends" aria-labelledby={`${tabsId}-heading`}>
      <header>
        <p className="ai-daily-eyebrow">GLOBAL SIGNALS</p>
        <h2 id={`${tabsId}-heading`} className="ai-daily-serif">全球 AI 应用趋势洞察</h2>
      </header>

      <div className="ai-trend-tabs" role="tablist" aria-label="趋势时间范围">
        {trendData.windows.map((snapshot) => (
          <button
            aria-controls={`${tabsId}-${snapshot.window}`}
            aria-selected={activeWindow === snapshot.window}
            id={`${tabsId}-${snapshot.window}-tab`}
            key={snapshot.window}
            onClick={() => setActiveWindow(snapshot.window)}
            role="tab"
            type="button"
          >
            {labels[snapshot.window]}
          </button>
        ))}
      </div>

      <div
        aria-labelledby={`${tabsId}-${active.window}-tab`}
        className="ai-trend-panel"
        id={`${tabsId}-${active.window}`}
        role="tabpanel"
      >
        <p className="ai-trend-range">
          {formatShortDate(active.rangeStart)}—{formatShortDate(active.rangeEnd)}
          <span>
            {active.mode === 'curated'
              ? `编辑策展 · ${sourceCount(active)} 个来源`
              : `${active.coverageCount} 期日报归纳`}
          </span>
        </p>
        <ol>
          {active.insights.map((insight, index) => (
            <li key={insight.title}>
              <span className="ai-trend-index">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <h3 className="ai-daily-serif">{insight.title}</h3>
                <p>{insight.summary}</p>
                <details>
                  <summary>查看依据（{insight.sources.length}）</summary>
                  <ul>
                    {insight.sources.map((source) => (
                      <li key={source.url}>
                        <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                        <time dateTime={source.publishedAt}>{source.publishedAt}</time>
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </aside>
  )
}
