import { cn } from '@/lib/class-names'
import { MESSAGES } from '@/messages'

/** The name and the tagline of Platita: over the way in, and at the top of the side menu. */
export function Brand({ inverted = false }: { inverted?: boolean }) {
  return (
    <div className="px-3">
      <h1 className={cn('text-2xl font-bold tracking-tight', inverted ? 'text-sidebar-primary' : 'text-primary')}>
        {MESSAGES.appTitle}
      </h1>
      <p className={cn('text-sm', inverted ? 'text-sidebar-muted' : 'text-muted-foreground')}>{MESSAGES.appTagline}</p>
    </div>
  )
}
