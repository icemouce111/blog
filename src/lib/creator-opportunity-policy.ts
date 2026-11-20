export type RewardType = 'cash_prize' | 'cash_fee' | 'commission' | 'credits' | 'traffic'

export interface CreatorOpportunity {
  id: string
  title: string
  organizer: string
  type: string
  url: string
  sourceUrl?: string
  rewardTypes: RewardType[]
  reward: string
  requirements: string
  deadline: string | null
  deadlineKind: 'dated' | 'rolling' | 'unknown' | 'conflicting'
  deadlineText: string
  fitStage: 'now' | 'apply' | 'later'
  fit: string
  minFollowers: number | null
  priority: number
  verification: 'official' | 'pending'
  verifiedAt: string | null
  checkedAt: string | null
  pendingReason?: string
  checkNote?: string
  discoveryPlatform?: 'xiaohongshu' | 'douyin' | 'x' | 'wechat'
  reviewMode?: 'manual'
}

export interface CreatorProfile {
  followersBelow: number
  weeklyHours: number
  verificationMaxAgeDays: number
}

export const rewardLabels: Record<RewardType, string> = {
  cash_prize: '现金竞赛',
  cash_fee: '任务／内容收入',
  commission: '成交佣金',
  credits: '积分／工具资源',
  traffic: '流量扶持',
}

function dayNumber(value: string | null) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const stamp = Date.parse(`${value}T00:00:00Z`)
  if (!Number.isFinite(stamp) || new Date(stamp).toISOString().slice(0, 10) !== value) return null
  return stamp / 86_400_000
}

export function classifyOpportunity(
  item: CreatorOpportunity,
  referenceDate: string,
  profile: CreatorProfile,
) {
  const reference = dayNumber(referenceDate)
  const deadline = dayNumber(item.deadline)
  if (reference === null) return 'pending'
  if (deadline !== null && deadline < reference) return 'expired'
  const verified = dayNumber(item.verifiedAt)
  if (
    item.verification !== 'official' ||
    verified === null ||
    verified > reference ||
    reference - verified > profile.verificationMaxAgeDays ||
    !['dated', 'rolling'].includes(item.deadlineKind) ||
    (item.deadlineKind === 'dated' && deadline === null) ||
    !item.reward ||
    !item.rewardTypes?.length ||
    !item.requirements ||
    !item.url ||
    !item.fit
  )
    return 'pending'
  if (
    item.fitStage === 'later' ||
    (item.minFollowers !== null && item.minFollowers >= profile.followersBelow)
  )
    return 'later'
  return 'recommended'
}

export function groupOpportunities(
  items: CreatorOpportunity[],
  referenceDate: string,
  profile: CreatorProfile,
) {
  const groups = {
    recommended: [] as CreatorOpportunity[],
    pending: [] as CreatorOpportunity[],
    later: [] as CreatorOpportunity[],
  }
  for (const item of items) {
    const group = classifyOpportunity(item, referenceDate, profile)
    if (group !== 'expired') groups[group].push(item)
  }
  for (const group of Object.values(groups)) {
    group.sort(
      (a, b) =>
        a.priority - b.priority ||
        (a.deadline || '9999-12-31').localeCompare(b.deadline || '9999-12-31') ||
        a.id.localeCompare(b.id),
    )
  }
  return groups
}

export function pendingReason(
  item: CreatorOpportunity,
  referenceDate: string,
  profile: CreatorProfile,
) {
  if (item.pendingReason) return item.pendingReason
  const reference = dayNumber(referenceDate)
  const verified = dayNumber(item.verifiedAt)
  if (
    verified !== null &&
    reference !== null &&
    reference - verified > profile.verificationMaxAgeDays
  )
    return '上次核验已超过有效期，需重新确认规则'
  return '奖励、资格或截止时间尚未完整核实'
}
