import opportunitySeed from '@/data/ai-opportunities.json'
import sourceConfig from '@/data/creator-opportunity-sources.json'
import { groupOpportunities, type CreatorOpportunity } from './creator-opportunity-policy'

export type AiOpportunity = CreatorOpportunity

interface OpportunitySeed {
  updatedAt: string
  opportunities: CreatorOpportunity[]
  collection: { date?: string; searchFailures?: number; pageFailures?: number; modelStatus?: string }
}

const seed = opportunitySeed as OpportunitySeed

export function todayInShanghai() {
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Asia/Shanghai',
  }).format(new Date())
}

export function getOpportunityGroups(referenceDate = todayInShanghai()) {
  return groupOpportunities(seed.opportunities, referenceDate, sourceConfig.profile)
}

export function getActiveAiOpportunities(referenceDate = todayInShanghai()) {
  return getOpportunityGroups(referenceDate).recommended
}

export function getOpportunityWatchSources() { return sourceConfig.watchSources }
export function getOpportunityCollection() { return { updatedAt: seed.updatedAt, ...seed.collection } }
export function getOpportunityProfile() { return sourceConfig.profile }
