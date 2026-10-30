import { cn } from '@/lib/utils'

const sizes = {
  default: 'max-w-[1200px]',
  narrow: 'max-w-3xl',
  wide: 'max-w-[1200px]',
} as const

type PageContainerSize = keyof typeof sizes

interface PageContainerProps {
  size?: PageContainerSize
  className?: string
  children: React.ReactNode
}

export function PageContainer({ size = 'default', className, children }: PageContainerProps) {
  return (
    <div className={cn('site-container site-page-container mx-auto', sizes[size], className)}>
      {children}
    </div>
  )
}
