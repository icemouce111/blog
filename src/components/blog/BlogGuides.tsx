import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import guides from '@/data/blog-guides.json'
import type { PostMeta } from '@/lib/posts'

export function BlogGuides({ posts }: { posts: PostMeta[] }) {
  return (
    <section className="blog-guides" aria-labelledby="blog-guides-heading">
      <div className="site-home-section-heading">
        <div>
          <p className="site-eyebrow">START HERE</p>
          <h2 id="blog-guides-heading">第一次来，可以从这里开始</h2>
        </div>
      </div>
      <nav className="site-focus-grid" aria-label="按问题开始阅读">
        {guides.map((guide) => {
          const firstPost = posts.find((post) => post.slug === guide.slugs[0])
          if (!firstPost) return null
          return (
            <Link
              className="site-panel site-focus-card blog-guide"
              key={guide.label}
              to={`/blog/${firstPost.slug}`}
            >
              <span className="site-eyebrow">{guide.label} · {guide.slugs.length} 篇</span>
              <h3>{guide.title}</h3>
              <p>{guide.description}</p>
              <span className="blog-guide-link">
                开始阅读 <ArrowRight aria-hidden="true" />
              </span>
            </Link>
          )
        })}
      </nav>
    </section>
  )
}
