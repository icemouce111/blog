import { Code2, ExternalLink, FolderGit2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import projectsData from '@/data/projects.json'
import { PageContainer } from '@/components/layout/PageContainer'
import { SectionHero } from '@/components/layout/SectionHero'

interface Project {
  name: string
  description: string
  tags: string[]
  github?: string
  demo?: string
}

export function ProjectsPage() {
  const projects = projectsData as Project[]

  return (
    <div className="site-page">
      <PageContainer size="wide">
        <SectionHero
          eyebrow="BUILDING / SHIPPING"
          title="作品集"
          description="不只展示完成品，也保留从需求、原型到可运行工具的实践过程。"
          icon={FolderGit2}
          meta={`${projects.length} 个公开项目`}
          tone="cyan"
        />

        {projects.length === 0 ? (
          <div className="site-panel py-16 text-center text-muted-foreground">项目陆续添加中…</div>
        ) : (
          <div className="site-project-grid site-tone-cyan">
            {projects.map((project, index) => (
              <Card key={project.name} className="site-card site-project-card">
                <CardHeader>
                  <div className="flex items-center justify-between gap-4">
                    <span className="site-card-index">PROJECT {String(index + 1).padStart(2, '0')}</span>
                    <span className="site-chip">可验证实践</span>
                  </div>
                  <CardTitle>{project.name}</CardTitle>
                  <CardDescription className="leading-6">{project.description}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col">
                  <div className="flex flex-wrap gap-1.5">
                    {project.tags.map((tag) => <span className="site-chip" key={tag}>{tag}</span>)}
                  </div>
                  <div className="site-project-actions">
                    {project.github && (
                      <Button variant="outline" size="sm" render={<a href={project.github} target="_blank" rel="noopener noreferrer" />}>
                        <Code2 className="h-4 w-4" /> GitHub
                      </Button>
                    )}
                    {project.demo && (
                      <Button size="sm" render={<a href={project.demo} target="_blank" rel="noopener noreferrer" />}>
                        <ExternalLink className="h-4 w-4" /> 演示
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </PageContainer>
    </div>
  )
}
