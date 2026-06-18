import { ExternalLink, MessageCircle, Mail } from 'lucide-react'
import { Separator } from '@/components/ui/separator'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import friendsData from '@/data/friends.json'

interface Friend {
  name: string
  url: string
  description: string
}

export function AboutPage() {
  const friends = friendsData as Friend[]

  return (
    <div className="container mx-auto max-w-3xl px-4 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">关于</h1>
        <p className="text-muted-foreground">个人简介</p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none">
        <p className="text-lg leading-7 text-muted-foreground">
          内容待补充...
        </p>

        <Separator className="my-8" />

        <h2 className="text-xl font-semibold mb-4">联系方式</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex items-center gap-3 rounded-lg border p-4">
            <MessageCircle className="h-5 w-5 text-green-500 shrink-0" />
            <div>
              <p className="text-sm font-medium">微信</p>
              <p className="text-sm text-muted-foreground font-mono">icemouce101（注明来意）</p>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg border p-4">
            <Mail className="h-5 w-5 text-blue-500 shrink-0" />
            <div>
              <p className="text-sm font-medium">邮箱</p>
              <p className="text-sm text-muted-foreground font-mono">2925547464@qq.com</p>
            </div>
          </div>
        </div>

        <Separator className="my-8" />

        <h2 className="text-xl font-semibold mb-4">友链</h2>
        {friends.length === 0 || (friends.length === 1 && !friends[0].url) ? (
          <p className="text-sm text-muted-foreground">友链待添加...</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {friends.map((friend) => (
              <Card key={friend.name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{friend.name}</CardTitle>
                  <CardDescription className="text-xs">{friend.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  {friend.url ? (
                    <Button variant="outline" size="sm" render={<a href={friend.url} target="_blank" rel="noopener noreferrer" />}>
                      <ExternalLink className="h-3 w-3 mr-1" />
                      访问
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground italic">链接待添加</span>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Separator className="my-8" />

        <h2 className="text-xl font-semibold mb-4">技能 & 工具</h2>
        <div className="flex flex-wrap gap-2">
          {[
            'TypeScript', 'React', 'Vite', 'Tailwind CSS',
            'Node.js', 'Cloudflare', 'PostgreSQL', 'Drizzle ORM',
          ].map((skill) => (
            <span
              key={skill}
              className="inline-flex items-center rounded-md bg-muted px-3 py-1 text-sm"
            >
              {skill}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
