import { ButtonLink } from '@/components/ui/button-link'
import { ExternalLink, LibraryBig, ShieldAlert } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
  sections: { name: string; items: ResourceItem[] }[]
}

export function ResourcesPage() {
  const categories: ResourceCategory[] = resourcesData.categories

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
                {category.sections.map((section) => (
                  <section key={section.name}>
                    <h2 className="mb-4 text-lg font-semibold">{section.name}</h2>
                    <div className="site-resource-grid site-tone-amber">
                      {section.items.map((item) => (
                        <Card key={item.url} className="site-card site-resource-card">
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
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </section>
                ))}
              </TabsContent>
            ))}
          </Tabs>
        </div>
      </PageContainer>
    </div>
  )
}
