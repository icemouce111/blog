import { ChevronDown } from 'lucide-react'
import { Disclosure } from '@/components/ui/disclosure'
import type { GithubDailyPost } from '@/lib/github-daily'
import { AiOpportunityRadar } from './AiOpportunityRadar'
import { AiTrendInsights } from './AiTrendInsights'
import { GithubDailyDigest } from './GithubDailyDigest'

interface AiDailySupplementsProps {
  githubPost?: GithubDailyPost | null
  showOpportunities?: boolean
  showTrends?: boolean
  fullOpportunities?: boolean
}

export function AiDailySupplements({
  githubPost,
  showOpportunities = true,
  showTrends = false,
  fullOpportunities = false,
}: AiDailySupplementsProps) {
  if (!githubPost && !showOpportunities && !showTrends) return null
  return (
    <Disclosure className="ai-daily-extras" id="daily-extras">
      <summary>
        <span className="ai-daily-extras-copy">
          <strong>工具与机会</strong>
          <span>继续探索开源项目、创作者合作与实践线索</span>
        </span>
        <span className="ai-daily-extras-action">
          <span className="ai-daily-extras-closed">展开</span>
          <span className="ai-daily-extras-open">收起</span>
          <ChevronDown aria-hidden="true" />
        </span>
      </summary>
      <div className="ai-daily-extras-body">
        {githubPost && <GithubDailyDigest post={githubPost} />}
        {showOpportunities && <AiOpportunityRadar variant={fullOpportunities ? 'issue' : 'index'} number="" />}
        {showTrends && <AiTrendInsights />}
      </div>
    </Disclosure>
  )
}
