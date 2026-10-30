import { Disclosure } from '@/components/ui/disclosure'
import { Link } from 'react-router-dom'
import {
  getOpportunityCollection,
  getOpportunityChannelCoverage,
  getOpportunitySearchIntervalDays,
  getOpportunityGroups,
  getOpportunityProfile,
  getOpportunityWatchSources,
  todayInShanghai,
} from '@/lib/ai-opportunities'
import { getAiDailyPosts } from '@/lib/ai-daily'
import {
  pendingReason,
  rewardLabels,
  type CreatorOpportunity,
} from '@/lib/creator-opportunity-policy'

interface AiOpportunityRadarProps {
  variant?: 'index' | 'issue'
  id?: string
  number?: string
}

function OpportunityList({
  items,
  pending = false,
}: {
  items: CreatorOpportunity[]
  pending?: boolean
}) {
  const reference = todayInShanghai()
  return (
    <ol className="ai-opportunity-list">
      {items.map((item) => (
        <li key={item.id}>
          <div className="ai-opportunity-topline">
            <span>
              {pending
                ? '待核实'
                : item.fitStage === 'later'
                  ? '后续再看'
                  : item.fitStage === 'apply'
                    ? '可准备申请'
                    : '可准备投稿'}
            </span>
            <span>{item.type}</span>
          </div>
          <h3>{item.title}</h3>
          <div className="ai-opportunity-badges">
            {item.rewardTypes.map((type) => (
              <span key={type}>{rewardLabels[type]}</span>
            ))}
            {!item.rewardTypes.length && <span>奖励类型待核</span>}
          </div>
          <p className="ai-opportunity-reward">{item.reward}</p>
          <dl className="ai-opportunity-facts">
            <div>
              <dt>关键门槛</dt>
              <dd>
                {item.minFollowers != null && item.minFollowers > 0
                  ? `至少 ${item.minFollowers.toLocaleString('zh-CN')} 粉丝；`
                  : ''}
                {item.requirements.split(/[；;。]/)[0]}
                {item.requirements.split(/[；;。]/).length > 1 ? '；完整要求见下方' : ''}
              </dd>
            </div>
            <div>
              <dt>截止时间</dt>
              <dd>{item.deadlineText}</dd>
            </div>
            {pending && (
              <div className="ai-opportunity-pending">
                <dt>还需确认</dt>
                <dd>{pendingReason(item, reference, getOpportunityProfile())}</dd>
              </div>
            )}
          </dl>
          <Disclosure className="ai-opportunity-detail">
            <summary>完整要求与适配说明</summary>
            <dl className="ai-opportunity-facts">
              <div>
                <dt>参与要求</dt>
                <dd>{item.requirements}</dd>
              </div>
              <div>
                <dt>适合怎样尝试</dt>
                <dd>{item.fit}</dd>
              </div>
            </dl>
          </Disclosure>
          <div className="ai-opportunity-foot">
            {item.url ? (
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                {pending ? '官方入口（细则待核）' : '查看官方规则'} ↗
              </a>
            ) : item.sourceUrl ? (
              <a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">
                查看线索（官方入口待确认） ↗
              </a>
            ) : null}
            {item.verifiedAt && (
              <span>
                核验 {item.verifiedAt}
                {item.checkNote ? ' · 本次检查未完成' : ''}
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}

function RadarContent({ compact }: { compact: boolean }) {
  const groups = getOpportunityGroups()
  const collection = getOpportunityCollection()
  const latest = getAiDailyPosts()[0]
  const limit = compact ? 3 : 5
  const failed = Boolean(
    collection.searchFailures || collection.pageFailures || collection.modelStatus === 'failed',
  )
  return (
    <>
      <p className="ai-daily-section-intro">
        按起步阶段、每周 5—10 小时筛选短视频活动、AI
        制作与合作渠道。现金、佣金、积分和流量分开；申请仍须审核，奖池不等于个人保底。
      </p>
      <p className="ai-opportunity-update">
        最近搜集：{collection.date || collection.updatedAt}
        {failed ? ' · 部分来源待复核' : ''}
      </p>
      <p className="ai-opportunity-update">
        四平台定向检索：每 {getOpportunitySearchIntervalDays()} 天一轮，未到期时沿用上次结果。
      </p>
      <ul className="ai-opportunity-channel-status" aria-label="四平台定向搜集状态">
        {getOpportunityChannelCoverage().map(({ id, name, result }) => (
          <li key={id}>
            <strong>{name}</strong>
            <span>
              {result
                ? `${result.skipped ? '上次：' : ''}${result.completed}/${result.queries} 次搜索 · ${result.leads ? `${result.leads} 条候选／${result.discovered} 条新增` : '未命中有效线索'}${result.failures ? ` · ${result.failures} 次失败` : ''}`
                : '待首次定向搜集'}
            </span>
            {result?.lastSearchedAt && (
              <span>
                搜集 {result.lastSearchedAt} · 下次 {result.nextSearchAt}
              </span>
            )}
          </li>
        ))}
      </ul>
      {Boolean(collection.reviewQueue?.length) && (
        <p className="ai-opportunity-update">
          平台待核队列：{collection.reviewQueue?.length}{' '}
          项。搜索完成不表示已核验官方账号及参与资格。
        </p>
      )}
      <h3 className="ai-opportunity-group-title">
        优先尝试 <span>{groups.recommended.length}</span>
      </h3>
      {groups.recommended.length ? (
        <OpportunityList items={groups.recommended.slice(0, limit)} />
      ) : (
        <p className="ai-opportunity-empty">暂无核验有效且适合当前阶段的机会。</p>
      )}
      {groups.recommended.length > limit && !compact && (
        <Disclosure className="ai-opportunity-more">
          <summary>其余可准备的机会（{groups.recommended.length - limit}）</summary>
          <OpportunityList items={groups.recommended.slice(limit)} />
        </Disclosure>
      )}
      {compact ? (
        <div className="ai-opportunity-index-footer">
          <p>
            另有 {groups.pending.length} 条待核实线索 · {groups.later.length} 项后续机会
          </p>
          {latest && (
            <Link className="site-text-link" to={`/ai-daily/${latest.slug}#creator-opportunities`}>
              查看全部机会与待核说明 →
            </Link>
          )}
        </div>
      ) : (
        <>
          <h3 className="ai-opportunity-group-title">
            待核实线索 <span>{groups.pending.length}</span>
          </h3>
          <p className="ai-opportunity-empty">
            奖励、账号资格、截止或活动细则尚未确认，不能视为可领取奖金或已接订单。
          </p>
          <OpportunityList items={groups.pending.slice(0, 3)} pending />
          {groups.pending.length > 3 && (
            <Disclosure className="ai-opportunity-more">
              <summary>查看其余待核线索（{groups.pending.length - 3}）</summary>
              <OpportunityList items={groups.pending.slice(3)} pending />
            </Disclosure>
          )}
          {groups.later.length > 0 && (
            <Disclosure className="ai-opportunity-more">
              <summary>达到门槛或有更多时间后再看（{groups.later.length}）</summary>
              <OpportunityList items={groups.later} />
            </Disclosure>
          )}
          <Disclosure className="ai-opportunity-sources">
            <summary>日常搜集的官方入口</summary>
            <ul>
              {getOpportunityWatchSources().map((source) => (
                <li key={source.url}>
                  <a href={source.url} target="_blank" rel="noopener noreferrer">
                    {source.name}
                  </a>
                </li>
              ))}
            </ul>
          </Disclosure>
        </>
      )}
    </>
  )
}

export function AiOpportunityRadar({
  variant = 'index',
  id = 'creator-opportunities',
  number = '09',
}: AiOpportunityRadarProps) {
  return (
    <section
      className={
        variant === 'issue'
          ? 'ai-daily-content-section ai-opportunity-section'
          : 'ai-opportunity-radar'
      }
      id={id}
      aria-labelledby={`${id}-heading`}
    >
      {variant === 'issue' ? (
        <div className="ai-daily-content-heading">
          <span>{number}</span>
          <h2 id={`${id}-heading`}>AI 创作者机会</h2>
        </div>
      ) : (
        <header>
          <p className="ai-daily-eyebrow">CREATOR RADAR</p>
          <h2 id={`${id}-heading`}>AI 创作者机会</h2>
        </header>
      )}
      <RadarContent compact={variant === 'index'} />
    </section>
  )
}
