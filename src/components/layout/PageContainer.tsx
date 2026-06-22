import { cn } from '@/lib/utils'

const sizes = {
  default: 'max-w-5xl',
  narrow: 'max-w-3xl',
  wide: 'max-w-6xl',
} as const

type PageContainerSize = keyof typeof sizes

interface PageContainerProps {
  size?: PageContainerSize
  className?: string
  children: React.ReactNode
}

export function PageContainer({
  size = 'default',
  className,
  children,
}: PageContainerProps) {
  return (
    <div className={cn('container mx-auto px-4 py-12', sizes[size], className)}>
      {children}
    </div>
  )
}
