import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AiDailyContent } from '@/components/ai-daily/AiDailyContent'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiOpportunityRadar } from '@/components/ai-daily/AiOpportunityRadar'
import { GithubDailyDigest } from '@/components/ai-daily/GithubDailyDigest'
import { ReadingLayout } from '@/components/reading/ReadingLayout'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import { getAiDailyPost, getAiDailyPosts } from '@/lib/ai-daily'
import type { AiDailySection } from '@/lib/ai-daily-parser'
import { getGithubDailyForDate } from '@/lib/github-daily'
import { getGithubDigestLabel } from '@/lib/github-daily-digest'
import { getActiveAiOpportunities } from '@/lib/ai-opportunities'

function getNextSectionNumber(sections: AiDailySection[]) {
  const largest = Math.max(0, ...sections.map((section) => Number(section.number) || 0))
  return String(largest + 1).padStart(2, '0')
}

export function AiDailyPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = useMemo(() => (slug ? getAiDailyPost(slug) : null), [slug])
  const githubPost = post ? getGithubDailyForDate(post.dateISO) : null
  const showOpportunities = Boolean(post && getAiDailyPosts()[0]?.slug === post.slug)
  const openSourceCount = Math.min(
    3,
    githubPost?.highlights.length || githubPost?.repos.length || 0,
  )
  const openSourceLabel = githubPost ? getGithubDigestLabel(githubPost) : undefined
  const opportunityCount = showOpportunities ? getActiveAiOpportunities().length : 0
  const prioritizeSupplements = Boolean(post?.isSignalArchive && (githubPost || showOpportunities))
  const contentSections = useMemo(() => {
    if (!post) return []
    const supplementCount = Number(Boolean(githubPost)) + Number(showOpportunities)
    return post.parsed.sections.map((section, index) => ({
      ...section,
      number: prioritizeSupplements
        ? String(supplementCount + index + 1).padStart(2, '0')
        : section.number,
      title: section.title.includes('原始信号归档') ? '今日来源速览' : section.title,
    }))
  }, [githubPost, post, prioritizeSupplements, showOpportunities])
  const supplemental = useMemo(() => {
    if (!post) return { sections: [] as AiDailySection[], githubNumber: '', opportunityNumber: '' }

    const sections: AiDailySection[] = []
    let nextNumber = prioritizeSupplements ? '01' : getNextSectionNumber(contentSections)
    const githubNumber = githubPost ? nextNumber : ''
    if (githubPost) {
      sections.push({
        number: nextNumber,
        title: `GitHub ${getGithubDigestLabel(githubPost)}`,
        id: 'github-picks',
        markdown: '',
      })
      nextNumber = String(Number(nextNumber) + 1).padStart(2, '0')
    }
    const opportunityNumber = showOpportunities ? nextNumber : ''
    if (showOpportunities) {
      sections.push({
        number: nextNumber,
        title: 'AI 创作者机会',
        id: 'creator-opportunities',
        markdown: '',
      })
    }
    return { sections, githubNumber, opportunityNumber }
  }, [contentSections, githubPost, post, prioritizeSupplements, showOpportunities])
  const navigationSections = useMemo(() => {
    if (!post) return []
    return prioritizeSupplements
      ? [...supplemental.sections, ...contentSections]
      : [...contentSections, ...supplemental.sections]
  }, [contentSections, post, prioritizeSupplements, supplemental.sections])

  const supplements = post ? (
    <>
      {githubPost && (
        <GithubDailyDigest
          id="github-picks"
          number={supplemental.githubNumber}
          post={githubPost}
          variant="issue"
        />
      )}
      {showOpportunities && (
        <AiOpportunityRadar
          id="creator-opportunities"
          number={supplemental.opportunityNumber}
          variant="issue"
        />
      )}
    </>
  ) : null

  if (!post) {
    return (
      <div className="ai-daily-shell">
        <PageContainer size="narrow" className="ai-daily-paper ai-daily-empty">
          <p className="ai-daily-eyebrow">404 / NOT FOUND</p>
          <h1 className="ai-daily-serif">这期日报不在档案中</h1>
          <Link className="ai-daily-back" to="/ai-daily">
            ← 返回情报归档
          </Link>
        </PageContainer>
      </div>
    )
  }

  return (
    <div className="ai-daily-shell">
      <PageContainer size="wide" className="ai-daily-paper">
        <Link className="ai-daily-back" to="/ai-daily">
          ← 返回情报归档
        </Link>
        <AiDailyMasthead date={post.date} issueId={post.issueId} />
        <ReadingLayout
          sections={navigationSections}
          directoryFooter={
            <>
              <p>
                {post.storyCount} 条信号 · {post.readingMinutes} 分钟阅读
              </p>
              <nav aria-label="相邻日报">
                {post.newerSlug && <Link to={`/ai-daily/${post.newerSlug}`}>← 更新一期</Link>}
                {post.olderSlug && <Link to={`/ai-daily/${post.olderSlug}`}>更早一期 →</Link>}
              </nav>
            </>
          }
        >
          <AiDailyContent
            afterSections={prioritizeSupplements ? null : supplements}
            beforeSections={prioritizeSupplements ? supplements : null}
            post={post}
            sections={contentSections}
            openSourceCount={openSourceCount}
            openSourceLabel={openSourceLabel}
            opportunityCount={opportunityCount}
          />
        </ReadingLayout>
      </PageContainer>
    </div>
  )
}
