import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { getReadingSections, type ReadingSection } from '@/lib/reading-navigation'

export function MarkdownContent({
  children,
  sections,
}: {
  children: string
  sections?: ReadingSection[]
}) {
  const headings = sections || getReadingSections(children)
  const components: Components = {
    h2: ({ node, children, ...props }) => (
      <h2 id={headings.find((item) => item.line === node?.position?.start.line)?.id} {...props}>
        {children}
      </h2>
    ),
    h3: ({ node, children, ...props }) => (
      <h3 id={headings.find((item) => item.line === node?.position?.start.line)?.id} {...props}>
        {children}
      </h3>
    ),
    a: ({ href, children }) => (
      <a
        href={href}
        {...(href?.startsWith('http') ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      >
        {children}
      </a>
    ),
    pre: ({ children }) => (
      <pre tabIndex={0} aria-label="可横向滚动的代码区域">
        {children}
      </pre>
    ),
    table: ({ children }) => (
      <div
        className="reading-table-scroll"
        role="region"
        aria-label="可横向滚动的表格"
        tabIndex={0}
      >
        <table>{children}</table>
      </div>
    ),
    img: ({ alt, ...props }) => <img {...props} alt={alt || ''} loading="lazy" decoding="async" />,
  }
  return (
    <div className="reading-prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
