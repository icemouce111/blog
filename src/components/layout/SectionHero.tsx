import type { LucideIcon } from 'lucide-react'

type SectionTone = 'violet' | 'cyan' | 'amber' | 'mixed'

interface SectionHeroProps {
  eyebrow: string
  title: string
  description: string
  icon: LucideIcon
  tone?: SectionTone
  meta?: string
}

export function SectionHero({
  eyebrow,
  title,
  description,
  icon: Icon,
  tone = 'violet',
  meta,
}: SectionHeroProps) {
  return (
    <header className={`site-section-hero site-tone-${tone}`}>
      <div className="site-section-hero-copy">
        <span className="site-section-mark" aria-hidden="true"><Icon /></span>
        <div>
          <p className="site-eyebrow">{eyebrow}</p>
          <h1 className="site-serif">{title}</h1>
          <p className="site-section-description">{description}</p>
        </div>
      </div>
      {meta && <p className="site-section-meta">{meta}</p>}
      <div className="site-section-orbit" aria-hidden="true" />
    </header>
  )
}
