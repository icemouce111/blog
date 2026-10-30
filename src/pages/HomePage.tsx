import { Link } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, BookOpen, FolderGit2, Link2, Wrench } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { PageContainer } from '@/components/layout/PageContainer'
import { ContentList } from '@/components/reading/ContentList'
import { getPosts } from '@/lib/posts'
import { getAiDailyPosts } from '@/lib/ai-daily'
import projects from '@/data/projects.json'

export function HomePage() {
  const posts = getPosts().slice(0, 3)
  const latest = getAiDailyPosts()[0]
  return (
    <div className="site-page">
      <PageContainer size="wide">
        <section className="site-home-hero" aria-labelledby="home-heading">
          <div className="site-home-intro">
            <img src="/avatar.jpg" alt="icemouce 的头像" />
            <span>ICEMOUCE / 学山</span>
          </div>
          <p className="site-eyebrow">持续学习，公开构建</p>
          <h1 id="home-heading">
            把 AI 放进真实工作，
            <br />
            把实践写成可用的经验。
          </h1>
          <p className="site-home-hero-copy">
            你好，我是学山。我在这里记录 Agent 工程、AI
            办公、全栈产品和真实业务实践，也把复杂工具翻译成普通人可以开始的第一步。
          </p>
          <div className="site-home-actions">
            <Link to="/projects">
              查看作品 <FolderGit2 aria-hidden="true" />
            </Link>
            <Link to="/blog">
              阅读文章 <BookOpen aria-hidden="true" />
            </Link>
          </div>
        </section>
        {projects.length > 0 && (
          <section className="site-home-section" aria-labelledby="home-projects-heading">
            <div className="site-home-section-heading">
              <div>
                <p className="site-eyebrow">SELECTED WORK</p>
                <h2 id="home-projects-heading">从想法到作品</h2>
              </div>
              <Link to="/projects">
                全部作品 <ArrowRight aria-hidden="true" />
              </Link>
            </div>
            <div className="site-project-grid">
              {projects.slice(0, 3).map((project, index) => (
                <Card className="site-card site-project-card" key={project.name}>
                  <CardHeader>
                    <p className="site-card-index">0{index + 1} / PROJECT</p>
                    <CardTitle role="heading" aria-level={3}>
                      {project.name}
                    </CardTitle>
                    <CardDescription>{project.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="content-list-tags">
                      {project.tags.slice(0, 3).map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                    <a
                      className="site-text-link"
                      href={project.github}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      查看项目 <ArrowUpRight aria-hidden="true" />
                    </a>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}
        {posts.length > 0 && (
          <section className="site-home-section" aria-labelledby="home-posts-heading">
            <div className="site-home-section-heading">
              <div>
                <p className="site-eyebrow">LATEST WRITING</p>
                <h2 id="home-posts-heading">最近写下的内容</h2>
              </div>
              <Link to="/blog">
                全部文章 <ArrowRight aria-hidden="true" />
              </Link>
            </div>
            <ContentList posts={posts} headingLevel={3} />
          </section>
        )}
        {latest && (
          <section
            className="site-home-section site-home-daily"
            aria-labelledby="home-daily-heading"
          >
            <div>
              <p className="site-eyebrow">AI DAILY / {latest.dateISO}</p>
              <h2 id="home-daily-heading">每天，筛出值得行动的变化。</h2>
              <p>{latest.leadTitle}</p>
            </div>
            <Link to={`/ai-daily/${latest.slug}`}>
              阅读最新一期 <ArrowRight aria-hidden="true" />
            </Link>
          </section>
        )}
        <section className="site-home-section site-home-quicklinks" aria-label="继续探索">
          <Link to="/resources">
            <Link2 aria-hidden="true" />
            <span>
              <strong>资源导航</strong>
              <small>长期整理的实用入口</small>
            </span>
            <ArrowUpRight aria-hidden="true" />
          </Link>
          <Link to="/tools">
            <Wrench aria-hidden="true" />
            <span>
              <strong>工具集</strong>
              <small>加入日常工作流的小帮手</small>
            </span>
            <ArrowUpRight aria-hidden="true" />
          </Link>
        </section>
      </PageContainer>
    </div>
  )
}
