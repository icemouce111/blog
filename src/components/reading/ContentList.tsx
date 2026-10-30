import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import type { PostMeta } from '@/lib/posts'

export function ContentList({
  posts,
  headingLevel = 2,
}: {
  posts: PostMeta[]
  headingLevel?: 2 | 3
}) {
  const Heading = headingLevel === 3 ? 'h3' : 'h2'
  return (
    <ol className="content-list">
      {posts.map((post) => (
        <li key={post.slug}>
          <Link to={`/blog/${post.slug}`} className="content-list-link">
            <time>{post.date}</time>
            <div>
              <Heading>{post.title}</Heading>
              <p>{post.description}</p>
              <div className="content-list-tags">
                {post.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </div>
            <ArrowUpRight aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ol>
  )
}
