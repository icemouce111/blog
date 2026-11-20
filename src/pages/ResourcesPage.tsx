import { ButtonLink } from '@/components/ui/button-link'
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
  note?: string
  action?: string
}

interface ResourceCategory {
  name: string
  key: string
  disclaimer?: string
  sections: { name: string; items: ResourceItem[] }[]
}

export function ResourcesPage() {
  const categories: ResourceCategory[] = resourcesData.categories
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <SectionHero
          eyebrow="PERSONAL COLLECTION"
          title="资源导航"
          description="查找大模型应用开发课程、Agent 电子书，以及影视和动漫入口。"
          icon={LibraryBig}
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
              <p className="mb-0 mt-2 leading-6">
                网盘分享由分享方维护。使用外部资源时，请遵守原作者的授权和平台规则。
              </p>
            </div>
          </div>
        </div>

        <div className="site-panel site-tabs-panel">
          <Tabs defaultValue={categories[0]?.key} className="w-full">
            <TabsList aria-label="资源类别" className="site-tabs-list mb-6 h-auto flex-wrap gap-1 bg-transparent p-0">
              {categories.map((category) => (
                <TabsTrigger key={category.key} value={category.key}>
                  {category.name}
                </TabsTrigger>
              ))}
            </TabsList>

            {categories.map((category) => (
              <TabsContent key={category.key} value={category.key} className="mt-0 space-y-8">
                {category.key === 'drive' && !disclaimerAccepted ? (
                  <div className="flex flex-col items-center justify-center px-4 py-16 text-center">
                    <AlertTriangle className="mb-4 h-12 w-12 text-amber-500" />
                    <h2 className="mb-2 text-lg font-semibold">网盘资源须知</h2>
                    <p className="mb-6 max-w-md text-sm leading-6 text-muted-foreground">
                      本板块仅汇总网友公开分享入口，请勿将内容用于商业或非法用途，并优先支持正版。
                    </p>
                    <Button onClick={() => setDisclaimerAccepted(true)}>已知悉，继续查看</Button>
                  </div>
                ) : (
                  <>
                    {category.disclaimer && (
                      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-muted-foreground">
                        <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
                        {category.disclaimer}
                      </div>
                    )}
                    {category.sections.map((section) => (
                      <section key={section.name}>
                        <h2 className="mb-4 text-lg font-semibold">{section.name}</h2>
                        <div className="site-resource-grid site-tone-amber">
                          {section.items.map((item) => (
                            <Card key={item.url || item.name} className="site-card site-resource-card">
                              <CardHeader>
                                <CardTitle>{item.name}</CardTitle>
                                <CardDescription className="leading-5">
                                  {item.description}
                                </CardDescription>
                              </CardHeader>
                              <CardContent className="mt-auto">
                                {item.note && (
                                  <p className="mb-3 text-xs leading-5 text-muted-foreground">
                                    {item.note}
                                  </p>
                                )}
                                {item.url ? (
                                  <ButtonLink
                                    variant="outline"
                                    size="sm"
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    aria-label={`${item.action ?? '访问'}：${item.name}`}
                                  >
                                    {item.action ?? '访问'} <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
                                  </ButtonLink>
                                ) : (
                                  <span className="text-xs italic text-muted-foreground">链接待添加</span>
                                )}
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      </section>
                    ))}
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
