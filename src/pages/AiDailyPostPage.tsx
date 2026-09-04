import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AiDailyContent } from '@/components/ai-daily/AiDailyContent'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import { AiOpportunityRadar } from '@/components/ai-daily/AiOpportunityRadar'
import { GithubDailyDigest } from '@/components/ai-daily/GithubDailyDigest'
import {
  AiDailyDesktopNavigation,
  AiDailyMobileNavigation,
} from '@/components/ai-daily/AiDailyNavigation'
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
  const [activeSection, setActiveSection] = useState('')
  const githubPost = post ? getGithubDailyForDate(post.dateISO) : null
  const showOpportunities = Boolean(post && getAiDailyPosts()[0]?.slug === post.slug)
  const openSourceCount = Math.min(3, githubPost?.highlights.length || githubPost?.repos.length || 0)
  const openSourceLabel = githubPost ? getGithubDigestLabel(githubPost) : undefined
  const opportunityCount = showOpportunities ? getActiveAiOpportunities(post?.dateISO).length : 0
  const prioritizeSupplements = Boolean(
    post?.isSignalArchive && (githubPost || showOpportunities)
  )
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
    let nextNumber = prioritizeSupplements
      ? '01'
      : getNextSectionNumber(contentSections)
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
      sections.push({ number: nextNumber, title: 'AI 创作者机会', id: 'creator-opportunities', markdown: '' })
    }
    return { sections, githubNumber, opportunityNumber }
  }, [contentSections, githubPost, post, prioritizeSupplements, showOpportunities])
  const navigationSections = useMemo(
    () => {
      if (!post) return []
      return prioritizeSupplements
        ? [...supplemental.sections, ...contentSections]
        : [...contentSections, ...supplemental.sections]
    },
    [contentSections, post, prioritizeSupplements, supplemental.sections]
  )

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

  useEffect(() => {
    if (!navigationSections.length) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActiveSection(visible[0].target.id)
      },
      { rootMargin: '-15% 0px -70% 0px' }
    )

    navigationSections.forEach((section) => {
      const element = document.getElementById(section.id)
      if (element) observer.observe(element)
    })

    return () => observer.disconnect()
  }, [navigationSections])

  if (!post) {
    return (
      <div className="ai-daily-shell">
        <PageContainer size="narrow" className="ai-daily-paper ai-daily-empty">
          <p className="ai-daily-eyebrow">404 / NOT FOUND</p>
          <h1 className="ai-daily-serif">这期日报不在档案中</h1>
          <Link className="ai-daily-back" to="/ai-daily">← 返回情报归档</Link>
        </PageContainer>
      </div>
    )
  }

  const scrollToSection = (id: string) => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    document.getElementById(id)?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'start',
    })
  }

  return (
    <div className="ai-daily-shell">
      <PageContainer size="wide" className="ai-daily-paper">
        <Link className="ai-daily-back" to="/ai-daily">← 返回情报归档</Link>
        <AiDailyMasthead date={post.date} issueId={post.issueId} />
        <AiDailyMobileNavigation sections={navigationSections} />
        <div className="ai-daily-layout">
          <article className="ai-daily-article">
            <AiDailyContent
              afterSections={prioritizeSupplements ? null : supplements}
              beforeSections={prioritizeSupplements ? supplements : null}
              post={post}
              sections={contentSections}
              openSourceCount={openSourceCount}
              openSourceLabel={openSourceLabel}
              opportunityCount={opportunityCount}
            />
          </article>
          <AiDailyDesktopNavigation
            activeSection={activeSection}
            onSectionClick={scrollToSection}
            post={post}
            sections={navigationSections}
          />
        </div>
      </PageContainer>
    </div>
  )
}
