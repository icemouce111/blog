import {
  getOpportunityCollection, getOpportunityGroups, getOpportunityProfile,
  getOpportunityWatchSources, todayInShanghai,
} from '@/lib/ai-opportunities'
import { pendingReason, rewardLabels, type CreatorOpportunity } from '@/lib/creator-opportunity-policy'

interface AiOpportunityRadarProps { variant?: 'index' | 'issue'; id?: string; number?: string }

function OpportunityList({ items, pending = false }: { items: CreatorOpportunity[]; pending?: boolean }) {
  const reference = todayInShanghai()
  return (
    <ol className="ai-opportunity-list">
      {items.map((item) => (
        <li key={item.id}>
          <div className="ai-opportunity-topline">
            <span>{pending ? '待核实' : item.fitStage === 'later' ? '后续再看' : item.fitStage === 'apply' ? '可准备申请' : '可准备投稿'}</span>
            <span>{item.type}</span>
          </div>
          <h3 className="ai-daily-serif">{item.title}</h3>
          <div className="ai-opportunity-badges">
            {item.rewardTypes.map((type) => <span key={type}>{rewardLabels[type]}</span>)}
            {!item.rewardTypes.length && <span>奖励类型待核</span>}
          </div>
          <p className="ai-opportunity-reward">{item.reward}</p>
          <dl className="ai-opportunity-facts">
            <div><dt>参与门槛</dt><dd>{item.requirements}</dd></div>
            <div><dt>截止时间</dt><dd>{item.deadlineText}</dd></div>
            <div><dt>{pending ? '还需确认' : '适合怎样尝试'}</dt><dd>{pending ? pendingReason(item, reference, getOpportunityProfile()) : item.fit}</dd></div>
          </dl>
          <p className="ai-opportunity-links">
            {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{pending ? '官方入口（细则待核）' : '查看官方规则'} ↗</a>
              : item.sourceUrl ? <a href={item.sourceUrl} target="_blank" rel="noreferrer">查看线索（官方入口待确认） ↗</a> : null}
          </p>
          {item.verifiedAt && <p className="ai-opportunity-verified">最近核验：{item.verifiedAt}{item.checkNote ? ' · 本次检查未完成' : ''}</p>}
        </li>
      ))}
    </ol>
  )
}

function RadarContent({ compact }: { compact: boolean }) {
  const groups = getOpportunityGroups()
  const collection = getOpportunityCollection()
  const limit = compact ? 3 : 5
  const failed = Boolean(collection.searchFailures || collection.pageFailures || collection.modelStatus === 'failed')
  return (
    <>
      <p className="ai-daily-section-intro">
        按起步阶段、每周 5—10 小时筛选短视频活动、AI 制作与合作渠道。现金、佣金、积分和流量分开；申请仍须主办方审核，奖池不等于个人保底。
      </p>
      <p className="ai-opportunity-update">最近搜集：{collection.date || collection.updatedAt}{failed ? ' · 部分来源待复核' : ''}</p>
      <h3 className="ai-opportunity-group-title">优先尝试</h3>
      {groups.recommended.length ? <OpportunityList items={groups.recommended.slice(0, limit)} />
        : <p className="ai-opportunity-empty">暂无核验有效且适合当前阶段的机会；下方线索仍需确认。</p>}
      {groups.recommended.length > limit && (
        <details className="ai-opportunity-more"><summary>其余可准备的机会（{groups.recommended.length - limit}）</summary>
          <OpportunityList items={groups.recommended.slice(limit)} />
        </details>
      )}
      <h3 className="ai-opportunity-group-title">待核实线索 <span>{groups.pending.length}</span></h3>
      <p className="ai-opportunity-empty">奖励、账号资格、截止或活动细则尚未确认，不能视为可领取奖金或已接订单。</p>
      <OpportunityList items={groups.pending.slice(0, 3)} pending />
      {groups.pending.length > 3 && (
        <details className="ai-opportunity-more"><summary>查看其余待核线索（{groups.pending.length - 3}）</summary>
          <OpportunityList items={groups.pending.slice(3)} pending />
        </details>
      )}
      {groups.later.length > 0 && (
        <details className="ai-opportunity-more"><summary>达到门槛或有更多时间后再看（{groups.later.length}）</summary>
          <OpportunityList items={groups.later} />
        </details>
      )}
      <details className="ai-opportunity-sources"><summary>日常搜集的官方入口</summary>
        <ul>{getOpportunityWatchSources().map((source) => (
          <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.name}</a></li>
        ))}</ul>
      </details>
    </>
  )
}

export function AiOpportunityRadar({ variant = 'index', id = 'creator-opportunities', number = '09' }: AiOpportunityRadarProps) {
  if (variant === 'issue') {
    return (
      <section className="ai-daily-content-section ai-daily-supplement ai-opportunity-section" id={id} aria-labelledby={`${id}-heading`}>
        <div className="ai-daily-content-heading"><span>{number}</span><h2 id={`${id}-heading`} className="ai-daily-serif">AI 创作者机会</h2></div>
        <RadarContent compact={false} />
      </section>
    )
  }
  return (
    <aside className="ai-opportunity-radar" aria-labelledby="opportunity-radar-heading">
      <header><p className="ai-daily-eyebrow">CREATOR RADAR</p>
        <h2 id="opportunity-radar-heading" className="ai-daily-serif">AI 创作者机会</h2>
      </header>
      <RadarContent compact />
    </aside>
  )
}
