import type { ComponentProps } from 'react'
import { cn } from '@/lib/class-names'

/**
 * The card of shadcn/ui (ADR 0027). It is a section, so that a screen that labels it with its
 * heading is announced as a region with that name.
 */
export function Card({ className, ...props }: ComponentProps<'section'>) {
  return (
    <section
      data-slot="card"
      className={cn('flex flex-col gap-4 rounded-xl border bg-card p-6 text-card-foreground shadow-sm', className)}
      {...props}
    />
  )
}

export function CardTitle({ className, ...props }: ComponentProps<'h2'>) {
  return <h2 data-slot="card-title" className={cn('text-base font-semibold leading-none', className)} {...props} />
}

export function CardDescription({ className, ...props }: ComponentProps<'p'>) {
  return <p data-slot="card-description" className={cn('text-sm text-muted-foreground', className)} {...props} />
}
