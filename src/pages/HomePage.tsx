import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, FolderGit2, Link2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { getPosts } from '@/lib/posts'
import { PageContainer } from '@/components/layout/PageContainer'

export function HomePage() {
  const posts = getPosts().slice(0, 3)

  const sections = [
    {
      title: '博客',
      description: '技术文章与思考',
      icon: BookOpen,
      href: '/blog',
      color: 'text-blue-500',
    },
    {
      title: '作品集',
      description: '项目与技术实践',
      icon: FolderGit2,
      href: '/projects',
      color: 'text-green-500',
    },
    {
      title: '资源导航',
      description: '影视动漫 & 网盘资源',
      icon: Link2,
      href: '/resources',
      color: 'text-purple-500',
    },
    {
      title: 'AI日报',
      description: '每日 AI 行业动态汇总',
      icon: Sparkles,
      href: '/ai-daily',
      color: 'text-orange-500',
    },
  ]

  return (
    <PageContainer>
      <section className="flex flex-col items-center text-center mb-16">
        <Avatar className="h-24 w-24 mb-6">
          <AvatarImage src="/avatar.jpg" alt="avatar" />
          <AvatarFallback className="text-2xl">IM</AvatarFallback>
        </Avatar>
        <h1 className="text-4xl font-bold tracking-tight mb-4">你好，我是 icemouce</h1>
        <p className="text-lg text-muted-foreground max-w-md">
          全栈开发者，热爱开源与技术分享
        </p>
      </section>

    <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        {sections.map((section) => (
          <Link key={section.href} to={section.href} className="group">
            <Card className="h-full transition-colors hover:border-primary/50 cursor-pointer">
              <CardHeader>
                <section.icon className={`h-8 w-8 mb-2 ${section.color}`} />
                <CardTitle className="group-hover:text-primary transition-colors">
                  {section.title}
                </CardTitle>
                <CardDescription>{section.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <span className="text-sm text-muted-foreground flex items-center gap-1 group-hover:text-foreground transition-colors">
                  探索更多 <ArrowRight className="h-3 w-3" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </section>

      {posts.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold tracking-tight">最新文章</h2>
              <Button variant="ghost" render={<Link to="/blog" />}>
                查看全部 <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
          </div>
          <Separator className="mb-6" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {posts.map((post) => (
              <Link key={post.slug} to={`/blog/${post.slug}`}>
                <Card className="h-full transition-colors hover:border-primary/50">
                  <CardHeader>
                    <CardTitle className="text-lg line-clamp-2">{post.title}</CardTitle>
                    <CardDescription className="text-xs">
                      {post.date}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {post.description}
                    </p>
                    {post.tags && post.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {post.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </>
      )}
    </PageContainer>
  )
}
