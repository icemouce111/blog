import { useEffect, useState, type MouseEvent, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { List, ArrowUpRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import {
  activeReadingSection,
  decodeReadingHash,
  type ReadingSection,
} from '@/lib/reading-navigation'

interface ReadingLayoutProps {
  sections: ReadingSection[]
  children: ReactNode
  directoryFooter?: ReactNode
}

function scrollToHeading(id: string, smooth: boolean) {
  const target = document.getElementById(id)
  if (!target) return
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ block: 'start', behavior: smooth && !reduced ? 'smooth' : 'auto' })
}

export function ReadingLayout({ sections, children, directoryFooter }: ReadingLayoutProps) {
  const { pathname, search, hash } = useLocation()
  const navigate = useNavigate()
  const [active, setActive] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const id = decodeReadingHash(hash)
    const frame = requestAnimationFrame(() => {
      if (id) scrollToHeading(id, false)
    })
    return () => cancelAnimationFrame(frame)
  }, [pathname, hash, sections])

  useEffect(() => {
    let frame = 0
    const update = () => {
      const offset =
        parseFloat(
          getComputedStyle(document.documentElement).getPropertyValue('--anchor-offset'),
        ) || 128
      setActive(
        activeReadingSection(
          sections.flatMap(({ id }) => {
            const element = document.getElementById(id)
            return element ? [{ id, top: element.getBoundingClientRect().top }] : []
          }),
          offset,
        ),
      )
    }
    const schedule = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(update)
    }
    schedule()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [sections, pathname])

  const select = (event: MouseEvent<HTMLAnchorElement>, id: string) => {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    setOpen(false)
    const nextHash = `#${encodeURIComponent(id)}`
    if (decodeReadingHash(hash) === id) scrollToHeading(id, true)
    else navigate({ pathname, search, hash: nextHash })
  }
  const links = () =>
    sections.map((section) => (
      <li key={section.id} className={section.level === 3 ? 'reading-toc-child' : undefined}>
        <a
          href={`#${encodeURIComponent(section.id)}`}
          onClick={(event) => select(event, section.id)}
          aria-current={active === section.id ? 'location' : undefined}
        >
          {section.number && <span className="reading-toc-number">{section.number}</span>}
          {section.title}
        </a>
      </li>
    ))

  return (
    <>
      {sections.length > 0 && (
        <div className="reading-mobile-bar">
          <span>{sections.find((section) => section.id === active)?.title || '本页目录'}</span>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger render={<Button variant="ghost" className="reading-directory-trigger" />}>
              <List aria-hidden="true" />
              目录
            </SheetTrigger>
            <SheetContent
              side="bottom"
              className="reading-directory-sheet"
              aria-describedby={undefined}
            >
              <SheetTitle>本页目录</SheetTitle>
              <nav aria-label="手机阅读目录">
                <ol className="reading-toc-list">{links()}</ol>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      )}
      <div className={`reading-layout${sections.length ? '' : ' reading-layout-solo'}`}>
        <article className="reading-article">{children}</article>
        {sections.length > 0 && (
          <aside className="reading-sidebar">
            <div className="reading-sidebar-sticky">
              <p className="site-eyebrow">
                本页目录 <ArrowUpRight aria-hidden="true" />
              </p>
              <nav aria-label="阅读目录">
                <ol className="reading-toc-list">{links()}</ol>
              </nav>
              {directoryFooter && <div className="reading-directory-footer">{directoryFooter}</div>}
            </div>
          </aside>
        )}
      </div>
    </>
  )
}
