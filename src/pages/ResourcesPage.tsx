import { useState } from 'react'
import { AlertTriangle, ExternalLink, LibraryBig, ShieldAlert } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import resourcesData from '@/data/resources.json'
import { PageContainer } from '@/components/layout/PageContainer'
import { SectionHero } from '@/components/layout/SectionHero'

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
  const resourceCount = categories.reduce((total, category) => total + category.items.length, 0)

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <SectionHero
          eyebrow="PERSONAL COLLECTION"
          title="资源导航"
          description="个人长期使用和整理的公开入口。先看用途与提示，再决定是否访问外部网站。"
          icon={LibraryBig}
          meta={`${resourceCount} 个入口`}
          tone="amber"
        />

        <div className="site-panel site-resource-notice">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div className="text-sm text-muted-foreground">
              <p className="mb-1 font-medium text-foreground">外部链接说明</p>
              <p className="m-0 leading-6">
                本站只整理公开链接，不存储或提供视频与文件资源。版权归原作者所有；访问外部页面时请注意广告、账号和个人信息安全。
              </p>
            </div>
          </div>
        </div>

        <div className="site-panel site-tabs-panel">
          <Tabs defaultValue={categories[0]?.key} className="w-full">
            <TabsList className="site-tabs-list mb-6 h-auto flex-wrap gap-1 bg-transparent p-0">
              {categories.map((category) => (
                <TabsTrigger key={category.key} value={category.key}>
                  {category.name}<span className="ml-1.5 text-xs text-muted-foreground">{category.items.length}</span>
                </TabsTrigger>
              ))}
            </TabsList>

            {categories.map((category) => (
              <TabsContent key={category.key} value={category.key} className="mt-0">
                {category.key === 'drive' && !disclaimerAccepted ? (
                  <div className="flex flex-col items-center justify-center px-4 py-16 text-center">
                    <AlertTriangle className="mb-4 h-12 w-12 text-amber-500" />
                    <h3 className="mb-2 text-lg font-semibold">网盘资源须知</h3>
                    <p className="mb-6 max-w-md text-sm leading-6 text-muted-foreground">
                      本板块仅汇总网友公开分享入口，请勿将内容用于商业或非法用途，并优先支持正版。
                    </p>
                    <Button onClick={() => setDisclaimerAccepted(true)}>已知悉，继续查看</Button>
                  </div>
                ) : category.items.length === 0 ? (
                  <div className="py-16 text-center text-muted-foreground">暂无资源，后续添加…</div>
                ) : (
                  <>
                    {category.disclaimer && (
                      <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-muted-foreground">
                        <AlertTriangle className="mr-1 inline h-3.5 w-3.5 text-amber-500" />
                        {category.disclaimer}
                      </div>
                    )}
                    <div className="site-resource-grid site-tone-amber">
                      {category.items.map((item) => (
                        <Card key={item.name} className="site-card site-resource-card">
                          <CardHeader>
                            <CardTitle>{item.name}</CardTitle>
                            <CardDescription className="leading-5">{item.description}</CardDescription>
                          </CardHeader>
                          <CardContent className="mt-auto">
                            {item.note && <p className="mb-3 text-xs leading-5 text-muted-foreground">{item.note}</p>}
                            {item.url ? (
                              <Button variant="outline" size="sm" render={<a href={item.url} target="_blank" rel="noopener noreferrer" />}>
                                访问 <ExternalLink className="h-3.5 w-3.5" />
                              </Button>
                            ) : (
                              <span className="text-xs italic text-muted-foreground">链接待添加</span>
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
      </PageContainer>
    </div>
  )
}
