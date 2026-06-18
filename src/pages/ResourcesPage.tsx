import { ExternalLink, AlertTriangle, ShieldAlert } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import resourcesData from '@/data/resources.json'
import { useState } from 'react'

interface ResourceItem {
  name: string
  url: string
  description: string
  note: string
}

interface ResourceCategory {
  name: string
  key: string
  items: ResourceItem[]
  disclaimer?: string
}

export function ResourcesPage() {
  const { categories } = resourcesData as { categories: ResourceCategory[] }
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)

  return (
    <div className="container mx-auto max-w-5xl px-4 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">资源导航</h1>
        <p className="text-muted-foreground">影视动漫 & 网盘资源合集</p>
      </div>

      <div className="mb-6 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4">
        <div className="flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-yellow-500 shrink-0 mt-0.5" />
          <div className="text-sm text-muted-foreground">
            <p className="font-medium text-foreground mb-1">免责声明</p>
            <p>
              本站仅为个人收集整理的外部链接导航页，不存储、不提供任何视频/文件资源。
              所有链接均来自互联网公开信息，版权归原作者所有。
              若权利人认为相关内容侵犯权益，请联系删除。
              访问外部链接前请自行安装广告拦截插件，注意个人信息安全。
            </p>
          </div>
        </div>
      </div>

      <Tabs defaultValue={categories[0]?.key} className="w-full">
        <TabsList className="mb-6 flex-wrap h-auto gap-1 bg-transparent p-0">
          {categories.map((cat) => (
            <TabsTrigger key={cat.key} value={cat.key} className="rounded-md">
              {cat.name}
              <span className="ml-1.5 text-xs text-muted-foreground">
                ({cat.items.length})
              </span>
            </TabsTrigger>
          ))}
        </TabsList>

        {categories.map((cat) => (
          <TabsContent key={cat.key} value={cat.key} className="mt-0">
            {cat.key === 'drive' && !disclaimerAccepted ? (
              <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
                <AlertTriangle className="h-12 w-12 text-yellow-500 mb-4" />
                <h3 className="text-lg font-semibold mb-2">网盘资源须知</h3>
                <p className="text-sm text-muted-foreground max-w-md mb-6">
                  本板块分享的资源仅供学习交流使用，请于下载后 24 小时内删除。
                  全部资源均来自网友公开分享，非本站存储。
                  禁止将本站资源用于商业或非法用途，如有需要请支持正版。
                </p>
                <Button onClick={() => setDisclaimerAccepted(true)}>
                  已知悉，继续查看
                </Button>
              </div>
            ) : cat.items.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                暂无资源，后续添加...
              </div>
            ) : (
              <>
                {cat.disclaimer && (
                  <div className="mb-4 rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 text-xs text-muted-foreground">
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 inline mr-1" />
                    {cat.disclaimer}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {cat.items.map((item) => (
                    <Card key={item.name} className="transition-colors hover:border-primary/50">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">{item.name}</CardTitle>
                        <CardDescription className="text-xs">{item.description}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {item.note && (
                          <p className="text-xs text-muted-foreground mb-3">{item.note}</p>
                        )}
                        {item.url ? (
                          <Button variant="outline" size="sm" render={<a href={item.url} target="_blank" rel="noopener noreferrer" />}>
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
              </>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
