import { ExternalLink } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import resourcesData from '@/data/resources.json'

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
}

export function ResourcesPage() {
  const { categories } = resourcesData as { categories: ResourceCategory[] }

  return (
    <div className="container mx-auto max-w-5xl px-4 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">资源导航</h1>
        <p className="text-muted-foreground">影视动漫 & 网盘资源合集</p>
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
            {cat.items.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                暂无资源，后续添加...
              </div>
            ) : (
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
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
