import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, FolderGit2, Link2, Sparkles } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getPosts } from '@/lib/posts'
import { PageContainer } from '@/components/layout/PageContainer'

const sections = [
  {
    title: '博客',
    description: '记录工程实践、产品判断与问题解决过程',
    eyebrow: 'WRITING',
    icon: BookOpen,
    href: '/blog',
    tone: 'violet',
  },
  {
    title: '作品集',
    description: '可以运行、验证和继续迭代的真实项目',
    eyebrow: 'BUILDING',
    icon: FolderGit2,
    href: '/projects',
    tone: 'cyan',
  },
  {
    title: '资源导航',
    description: '个人长期使用和整理的实用入口',
    eyebrow: 'COLLECTION',
    icon: Link2,
    href: '/resources',
    tone: 'amber',
  },
  {
    title: 'AI 情报',
    description: '从变化中筛出值得理解、实践和参与的信号',
    eyebrow: 'INTELLIGENCE',
    icon: Sparkles,
    href: '/ai-daily',
    tone: 'mixed',
  },
] as const

export function HomePage() {
  const posts = getPosts().slice(0, 3)

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <section className="site-home-hero" aria-labelledby="home-heading">
          <div className="site-home-copy">
            <div className="site-home-intro">
              <img src="/avatar.jpg" alt="" />
              ICEMOUCE · BUILD IN PUBLIC
            </div>
            <h1 id="home-heading">你好！我是学山，希望你有收获！</h1>
            <p className="site-home-hero-copy">
              我在这里记录 Agent 工程、AI 办公、全栈产品和真实业务实践，也把复杂工具翻译成普通人可以开始的第一步。
            </p>
            <div className="site-home-actions">
              <Link to="/ai-daily">进入 AI 情报站 <ArrowRight /></Link>
              <Link to="/projects">查看实践作品 <ArrowRight /></Link>
            </div>
          </div>
          <div className="site-home-monogram" aria-hidden="true">AI</div>
        </section>

        <section className="site-home-section" aria-labelledby="explore-heading">
          <div className="site-home-section-heading">
            <div>
              <p className="site-eyebrow">EXPLORE</p>
              <h2 id="explore-heading">从这里开始</h2>
            </div>
          </div>
          <div className="site-home-nav-grid">
            {sections.map((section) => (
              <Link key={section.href} to={section.href} className={`site-tone-${section.tone}`}>
                <Card className="site-card site-home-nav-card">
                  <CardHeader>
                    <span className="site-home-nav-icon"><section.icon /></span>
                    <p className="site-eyebrow">{section.eyebrow}</p>
                    <CardTitle>{section.title}</CardTitle>
                    <CardDescription>{section.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="mt-auto">
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      探索更多 <ArrowRight className="h-3 w-3" />
                    </span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {posts.length > 0 && (
          <section className="site-home-section" aria-labelledby="latest-posts-heading">
            <div className="site-home-section-heading">
              <div>
                <p className="site-eyebrow">LATEST NOTES</p>
                <h2 id="latest-posts-heading">最近写下的内容</h2>
              </div>
              <Link className="flex items-center gap-1 text-sm text-muted-foreground" to="/blog">
                查看全部 <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="site-blog-grid site-tone-violet">
              {posts.map((post, index) => (
                <Link key={post.slug} to={`/blog/${post.slug}`}>
                  <Card className="site-card site-blog-card">
                    <CardHeader>
                      <div className="flex items-center justify-between gap-4">
                        <span className="site-card-index">{String(index + 1).padStart(2, '0')}</span>
                        <time className="text-xs text-muted-foreground">{post.date}</time>
                      </div>
                      <CardTitle className="line-clamp-2">{post.title}</CardTitle>
                      <CardDescription className="line-clamp-3">{post.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="mt-auto">
                      <div className="flex flex-wrap gap-1.5">
                        {post.tags.slice(0, 3).map((tag) => <span className="site-chip" key={tag}>{tag}</span>)}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        )}
      </PageContainer>
    </div>
  )
}
