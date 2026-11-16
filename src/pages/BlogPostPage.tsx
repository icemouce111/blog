import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { GiscusComments } from '@/components/blog/GiscusComments'
import { PageContainer } from '@/components/layout/PageContainer'
import { ReadingLayout } from '@/components/reading/ReadingLayout'
import { MarkdownContent } from '@/components/reading/MarkdownContent'
import { getReadingSections } from '@/lib/reading-navigation'
import { getPost, getPosts } from '@/lib/posts'
import guides from '@/data/blog-guides.json'

export function BlogPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const { post, content, sections } = useMemo(() => {
    const post = slug ? getPost(slug) : null
    const content = post?.content.replace(/^\s*#\s+.+\n+/, '') || ''
    return { post, content, sections: getReadingSections(content) }
  }, [slug])
  const series = guides.find((guide) => guide.slugs.length > 1 && guide.slugs.includes(slug || ''))
  const allPosts = series ? getPosts() : []
  const seriesPosts = series
    ? series.slugs.flatMap((seriesSlug) => allPosts.filter((post) => post.slug === seriesSlug))
    : []
  if (!post)
    return (
      <PageContainer size="narrow">
        <h1>文章未找到</h1>
        <Link className="site-text-link" to="/blog">
          ← 返回博客
        </Link>
      </PageContainer>
    )
  return (
    <div className="site-page">
      <PageContainer size="wide">
        <Link className="site-back-link" to="/blog">
          <ArrowLeft aria-hidden="true" />
          返回博客
        </Link>
        <ReadingLayout sections={sections}>
          <header className="site-article-header">
            <p className="site-eyebrow">WRITING / NOTES</p>
            <h1>{post.title}</h1>
            <p>{post.description}</p>
            <div className="site-article-meta">
              <time dateTime={post.dateISO || undefined}>{post.date}</time>
              <div className="content-list-tags">
                {post.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </div>
          </header>
          <MarkdownContent sections={sections}>{content}</MarkdownContent>
          {series && (
            <nav className="blog-series site-panel" aria-label={`${series.label}系列阅读`}>
              <h2>继续阅读 · {series.label}</h2>
              <ol>
                {seriesPosts.map((item, index) => (
                  <li key={item.slug}>
                    <Link to={`/blog/${item.slug}`} aria-current={item.slug === slug ? 'page' : undefined}>
                      <span>{String(index + 1).padStart(2, '0')}</span>
                      {item.title}
                      {item.slug === slug && <small>正在阅读</small>}
                    </Link>
                  </li>
                ))}
              </ol>
            </nav>
          )}
          <div className="site-comments">
            <GiscusComments />
          </div>
        </ReadingLayout>
      </PageContainer>
    </div>
  )
}
