import { useMemo } from 'react'
import trendSeed from '@/data/ai-trends.json'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Disclosure } from '@/components/ui/disclosure'
import { parseAiTrendData, type TrendSnapshot, type TrendWindow } from '@/lib/ai-trends'

const labels: Record<TrendWindow, string> = { week: '近周', month: '近月', year: '近年' }
function formatShortDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    timeZone: 'Asia/Shanghai',
  }).format(new Date(`${value}T00:00:00+08:00`))
}
function TrendPanel({ snapshot }: { snapshot: TrendSnapshot }) {
  const sourceCount = new Set(
    snapshot.insights.flatMap((insight) => insight.sources.map((source) => source.url)),
  ).size
  return (
    <div className="ai-trend-panel">
      <p className="ai-trend-range">
        {formatShortDate(snapshot.rangeStart)}—{formatShortDate(snapshot.rangeEnd)}
        <span>
          {snapshot.mode === 'curated'
            ? `编辑策展 · ${sourceCount} 个来源`
            : `${snapshot.coverageCount} 期日报归纳`}
        </span>
      </p>
      <ol>
        {snapshot.insights.map((insight, index) => (
          <li key={insight.title}>
            <span className="ai-trend-index">{String(index + 1).padStart(2, '0')}</span>
            <div>
              <h3>{insight.title}</h3>
              <p>{insight.summary}</p>
              <Disclosure>
                <summary>查看依据（{insight.sources.length}）</summary>
                <ul>
                  {insight.sources.map((source) => (
                    <li key={source.url}>
                      <a href={source.url} target="_blank" rel="noopener noreferrer">
                        {source.title}
                      </a>
                      <time dateTime={source.publishedAt}>{source.publishedAt}</time>
                    </li>
                  ))}
                </ul>
              </Disclosure>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
export function AiTrendInsights() {
  const trendData = useMemo(() => parseAiTrendData(trendSeed), [])
  if (!trendData.windows.length) return null
  return (
    <section className="ai-trends" aria-labelledby="trend-heading">
      <header>
        <p className="ai-daily-eyebrow">GLOBAL SIGNALS</p>
        <h2 id="trend-heading">AI 应用趋势洞察</h2>
      </header>
      <Tabs defaultValue={trendData.windows[0].window}>
        <TabsList className="ai-trend-tabs" aria-label="趋势时间范围">
          {trendData.windows.map((snapshot) => (
            <TabsTrigger value={snapshot.window} key={snapshot.window}>
              {labels[snapshot.window]}
            </TabsTrigger>
          ))}
        </TabsList>
        {trendData.windows.map((snapshot) => (
          <TabsContent value={snapshot.window} key={snapshot.window}>
            <TrendPanel snapshot={snapshot} />
          </TabsContent>
        ))}
      </Tabs>
    </section>
  )
}
