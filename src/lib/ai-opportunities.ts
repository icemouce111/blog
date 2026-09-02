import opportunitySeed from '@/data/ai-opportunities.json'

export type OpportunityVerification = 'official'

export interface AiOpportunity {
  id: string
  priority: number
  title: string
  organizer: string
  type: string
  deadline: string | null
  reward: string
  fit: string
  url: string
  verification: OpportunityVerification
  note?: string
}

export interface OpportunityWatchSource {
  name: string
  url: string
}

interface OpportunitySeed {
  lastVerified: string
  opportunities: AiOpportunity[]
  watchSources: OpportunityWatchSource[]
}

const seed = opportunitySeed as OpportunitySeed

function todayInShanghai() {
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: 'Asia/Shanghai',
  }).format(new Date())
}

export function getActiveAiOpportunities(referenceDate = todayInShanghai()) {
  return seed.opportunities
    .filter((item) => item.verification === 'official')
    .filter((item) => !item.deadline || item.deadline >= referenceDate)
    .toSorted((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority
      if (!a.deadline && !b.deadline) return a.title.localeCompare(b.title, 'zh-CN')
      if (!a.deadline) return 1
      if (!b.deadline) return -1
      return a.deadline.localeCompare(b.deadline)
    })
}

export function getOpportunityWatchSources() {
  return seed.watchSources
}

export function getOpportunityLastVerified() {
  return seed.lastVerified
}

export function formatOpportunityDeadline(deadline: string | null) {
  if (!deadline) return '长期招募'
  const [, month, day] = deadline.split('-')
  return `${Number(month)} 月 ${Number(day)} 日截止`
}
