import { Separator } from '@/components/ui/separator'

export function AboutPage() {
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
