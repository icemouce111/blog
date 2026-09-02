import {
  BriefcaseBusiness,
  ExternalLink,
  GraduationCap,
  Mail,
  MessageCircle,
  UserRound,
  Workflow,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import friendsData from '@/data/friends.json'
import { PageContainer } from '@/components/layout/PageContainer'
import { SectionHero } from '@/components/layout/SectionHero'

interface Friend {
  name: string
  url: string
  description: string
}

const focusAreas = [
  {
    title: 'Agent 工程',
    description: '关注 Skills、MCP、上下文、记忆、评测，以及如何让工作流更可靠。',
    icon: Workflow,
  },
  {
    title: '真实业务落地',
    description: '把 AI 放进文档、知识库、业务复核和团队协作，而不只停留在演示。',
    icon: BriefcaseBusiness,
  },
  {
    title: '小白教学',
    description: '把复杂工具翻译成普通人能理解、能完成、能获得正反馈的第一步。',
    icon: GraduationCap,
  },
]

const skills = [
  'TypeScript', 'React', 'Vite', 'Tailwind CSS',
  'Node.js', 'Cloudflare', 'PostgreSQL', 'Drizzle ORM',
]

export function AboutPage() {
  const friends = friendsData as Friend[]
  const visibleFriends = friends.filter((friend) => friend.url)

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <SectionHero
          eyebrow="ABOUT / DIRECTION"
          title="关于"
          description="我关心的不是追逐每一次模型更新，而是 AI 能否真正进入工作、形成作品，并持续产生积累。"
          icon={UserRound}
          tone="mixed"
        />

        <div className="site-about-intro">
          <section className="site-panel site-about-statement">
            <h2>你好，我是 icemouce</h2>
            <p>
              我是一名持续学习和构建中的全栈开发者。目前主要探索 Agent 工程、AI 辅助开发与企业场景落地，并把真实实践整理成教程、工具和可以继续迭代的作品。
            </p>
          </section>
          <aside className="site-panel site-about-principle">
            <p>MY WORKING PRINCIPLE</p>
            <strong>即使暂时没人看，每次公开表达也应该让自己多一份可复用资产。</strong>
          </aside>
        </div>

        <section className="site-focus-grid" aria-label="目前关注方向">
          {focusAreas.map((area) => (
            <div className="site-panel site-focus-card" key={area.title}>
              <area.icon />
              <h3>{area.title}</h3>
              <p>{area.description}</p>
            </div>
          ))}
        </section>

        <section className="site-panel site-about-section" aria-labelledby="contact-heading">
          <p className="site-eyebrow">CONTACT</p>
          <h2 id="contact-heading">联系方式</h2>
          <div className="site-contact-grid">
            <div className="site-contact-card">
              <MessageCircle className="h-5 w-5 shrink-0 text-emerald-500" />
              <div>
                <p className="text-sm font-medium">微信</p>
                <p className="text-sm text-muted-foreground">icemouce101（注明来意）</p>
              </div>
            </div>
            <div className="site-contact-card">
              <Mail className="h-5 w-5 shrink-0 text-blue-500" />
              <div>
                <p className="text-sm font-medium">邮箱</p>
                <p className="text-sm text-muted-foreground">2925547464@qq.com</p>
              </div>
            </div>
          </div>
        </section>

        <section className="site-panel site-about-section" aria-labelledby="skills-heading">
          <p className="site-eyebrow">TOOLKIT</p>
          <h2 id="skills-heading">技能与工具</h2>
          <div className="flex flex-wrap gap-2">
            {skills.map((skill) => <span className="site-chip" key={skill}>{skill}</span>)}
          </div>
        </section>

        {visibleFriends.length > 0 && (
          <section className="site-panel site-about-section" aria-labelledby="friends-heading">
            <p className="site-eyebrow">FRIENDS</p>
            <h2 id="friends-heading">友链</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {visibleFriends.map((friend) => (
                <Card className="site-card" key={friend.name}>
                  <CardHeader>
                    <CardTitle>{friend.name}</CardTitle>
                    <CardDescription>{friend.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button variant="outline" size="sm" render={<a href={friend.url} target="_blank" rel="noopener noreferrer" />}>
                      访问 <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}
      </PageContainer>
    </div>
  )
}
