import { useEffect, useRef } from 'react'
import { useThemeStore } from '@/store/theme'

export function GiscusComments() {
  const ref = useRef<HTMLDivElement>(null)
  const resolvedTheme = useThemeStore((s) => s.resolvedTheme)

  useEffect(() => {
    const container = ref.current
    if (!container) return

    container.innerHTML = ''

    const script = document.createElement('script')
    script.src = 'https://giscus.app/client.js'
    script.setAttribute('data-repo', 'icemouce111/blog')
    script.setAttribute('data-repo-id', 'R_kgDO_NOT_SET')
    script.setAttribute('data-category', 'Announcements')
    script.setAttribute('data-category-id', 'DIC_kwDO_NOT_SET')
    script.setAttribute('data-mapping', 'pathname')
    script.setAttribute('data-strict', '0')
    script.setAttribute('data-reactions-enabled', '1')
    script.setAttribute('data-emit-metadata', '0')
    script.setAttribute('data-input-position', 'bottom')
    script.setAttribute('data-theme', resolvedTheme === 'dark' ? 'dark_dimmed' : 'light')
    script.setAttribute('data-lang', 'zh-CN')
    script.setAttribute('crossorigin', 'anonymous')
    script.async = true

    container.appendChild(script)
  }, [resolvedTheme])

  return <div ref={ref} className="mt-8" />
}
