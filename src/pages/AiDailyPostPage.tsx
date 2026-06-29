import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AiDailyContent } from '@/components/ai-daily/AiDailyContent'
import { AiDailyMasthead } from '@/components/ai-daily/AiDailyMasthead'
import {
  AiDailyDesktopNavigation,
  AiDailyMobileNavigation,
} from '@/components/ai-daily/AiDailyNavigation'
import '@/components/ai-daily/ai-daily.css'
import { PageContainer } from '@/components/layout/PageContainer'
import { getAiDailyPost } from '@/lib/ai-daily'

export function AiDailyPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const post = slug ? getAiDailyPost(slug) : null
  const [activeSection, setActiveSection] = useState('')

  useEffect(() => {
    if (!post?.parsed.sections.length) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActiveSection(visible[0].target.id)
      },
      { rootMargin: '-15% 0px -70% 0px' }
    )

    post.parsed.sections.forEach((section) => {
      const element = document.getElementById(section.id)
      if (element) observer.observe(element)
    })

    return () => observer.disconnect()
  }, [post])

  if (!post) {
    return (
      <div className="ai-daily-shell">
        <PageContainer size="narrow" className="ai-daily-paper ai-daily-empty">
          <p className="ai-daily-eyebrow">404 / NOT FOUND</p>
          <h1 className="ai-daily-serif">这期日报不在档案中</h1>
          <Link className="ai-daily-back" to="/ai-daily">← 返回日报归档</Link>
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
        <Link className="ai-daily-back" to="/ai-daily">← 返回日报归档</Link>
        <AiDailyMasthead date={post.date} issueId={post.issueId} />
        <AiDailyMobileNavigation parsed={post.parsed} />
        <div className="ai-daily-layout">
          <article className="ai-daily-article">
            <AiDailyContent post={post} />
          </article>
          <AiDailyDesktopNavigation
            activeSection={activeSection}
            onSectionClick={scrollToSection}
            post={post}
          />
        </div>
      </PageContainer>
    </div>
  )
}
