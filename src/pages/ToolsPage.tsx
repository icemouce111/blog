import { ExternalLink, ShieldAlert, Wrench } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import toolsData from '@/data/tools.json'
import { PageContainer } from '@/components/layout/PageContainer'
import { SectionHero } from '@/components/layout/SectionHero'

interface ToolItem {
  name: string
  url: string
  description: string
  note: string
}

export function ToolsPage() {
  const { disclaimer, items } = toolsData as { disclaimer: string; items: ToolItem[] }

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <SectionHero
          eyebrow="TOOLS"
          title="工具集"
          description="整理可以直接打开、试用和加入工作流的在线工具。先看用途与提示，再决定是否访问外部网站。"
          icon={Wrench}
          meta={`${items.length} 个工具`}
          tone="cyan"
        />

        <div className="site-panel site-resource-notice">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div className="text-sm text-muted-foreground">
              <p className="mb-1 font-medium text-foreground">工具使用说明</p>
              <p className="m-0 leading-6">{disclaimer}</p>
            </div>
          </div>
        </div>

        <div className="site-panel site-tabs-panel">
          <div className="site-resource-grid site-tone-cyan">
            {items.map((item) => (
              <Card key={item.name} className="site-card site-resource-card">
                <CardHeader>
                  <CardTitle>{item.name}</CardTitle>
                  <CardDescription className="leading-5">{item.description}</CardDescription>
                </CardHeader>
                <CardContent className="mt-auto">
                  {item.note && <p className="mb-3 text-xs leading-5 text-muted-foreground">{item.note}</p>}
                  <Button
                    variant="outline"
                    size="sm"
                    render={<a href={item.url} target="_blank" rel="noopener noreferrer" />}
                  >
                    访问 <ExternalLink className="h-3.5 w-3.5" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </PageContainer>
    </div>
  )
}
