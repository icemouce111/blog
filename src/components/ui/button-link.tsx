import type { ComponentPropsWithoutRef } from 'react'
import type { VariantProps } from 'class-variance-authority'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

/** Navigation keeps native link semantics and reuses the shared button styling. */
export function ButtonLink({
  variant = 'outline',
  size = 'sm',
  className,
  ...props
}: ComponentPropsWithoutRef<'a'> & VariantProps<typeof buttonVariants>) {
  return <a {...props} className={cn(buttonVariants({ variant, size }), className)} />
}
