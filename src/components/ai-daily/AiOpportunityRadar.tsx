import {
  formatOpportunityDeadline,
  getActiveAiOpportunities,
  getOpportunityWatchSources,
} from '@/lib/ai-opportunities'

interface AiOpportunityRadarProps {
  variant?: 'index' | 'issue'
  id?: string
  number?: string
}

function OpportunityList({ limit }: { limit?: number }) {
  const opportunities = getActiveAiOpportunities()
  const visible = typeof limit === 'number' ? opportunities.slice(0, limit) : opportunities

  if (!visible.length) {
    return <p className="ai-opportunity-empty">暂时没有仍在报名期的机会。</p>
  }

  return (
    <ol className="ai-opportunity-list">
      {visible.map((item) => (
        <li key={item.id}>
          <div className="ai-opportunity-topline">
            <span>{item.type}</span>
            <time dateTime={item.deadline ?? undefined}>
              {formatOpportunityDeadline(item.deadline)}
            </time>
          </div>
          <h3 className="ai-daily-serif">
            <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
          </h3>
          <p className="ai-opportunity-reward">{item.reward}</p>
          <p>{item.fit}</p>
        </li>
      ))}
    </ol>
  )
}

function WatchSources() {
  return (
    <details className="ai-opportunity-sources">
      <summary>官方活动入口</summary>
      <ul>
        {getOpportunityWatchSources().map((source) => (
          <li key={source.url}>
            <a href={source.url} target="_blank" rel="noreferrer">{source.name}</a>
          </li>
        ))}
      </ul>
    </details>
  )
}

export function AiOpportunityRadar({
  variant = 'index',
  id = 'creator-opportunities',
  number = '09',
}: AiOpportunityRadarProps) {
  if (variant === 'issue') {
    return (
      <section
        className="ai-daily-content-section ai-daily-supplement ai-opportunity-section"
        id={id}
        aria-labelledby={`${id}-heading`}
      >
        <div className="ai-daily-content-heading">
          <span>{number}</span>
          <h2 id={`${id}-heading`} className="ai-daily-serif">AI 创作者机会</h2>
        </div>
        <p className="ai-daily-section-intro">
          只展示仍可参与且能由官方页面确认的计划。优先选择能沉淀教程、案例或讲师经历的机会。
        </p>
        <OpportunityList limit={5} />
        <WatchSources />
      </section>
    )
  }

  return (
    <aside className="ai-opportunity-radar" aria-labelledby="opportunity-radar-heading">
      <header>
        <p className="ai-daily-eyebrow">CREATOR RADAR</p>
        <h2 id="opportunity-radar-heading" className="ai-daily-serif">近期可参与的 AI 创作机会</h2>
        <p>从“今天发生了什么”再往前一步：找到能动手、投稿并积累作品的官方入口。</p>
      </header>
      <OpportunityList limit={4} />
      <WatchSources />
    </aside>
  )
}
