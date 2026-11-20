import type { ComponentProps } from 'react'

/** Native Enter/Space behaviour, with Escape returning focus to its summary. */
export function Disclosure({ children, ...props }: ComponentProps<'details'>) {
  return (
    <details
      {...props}
      onKeyDown={(event) => {
        props.onKeyDown?.(event)
        if (event.key === 'Escape' && !event.defaultPrevented && event.currentTarget.open) {
          event.preventDefault()
          event.stopPropagation()
          event.currentTarget.open = false
          event.currentTarget.querySelector('summary')?.focus()
        }
      }}
    >
      {children}
    </details>
  )
}
