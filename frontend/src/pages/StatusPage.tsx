import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { checkReadiness, type Readiness } from '../api/health'
import { MESSAGES } from '../messages'

/**
 * The three states of this screen. It shows no user data, so it has no empty state
 * (docs/convenciones-de-desarrollo.md, section 2).
 */
type State = { kind: 'loading' } | { kind: 'content' } | { kind: 'error'; cause: ErrorCause }

type ErrorCause = Exclude<Readiness['kind'], 'ready' | 'cancelled'>

const TEXT = MESSAGES.status

const ERROR_MESSAGES: Record<ErrorCause, string> = {
  'database-unreachable': TEXT.databaseUnreachable,
  ...MESSAGES.common.apiFailures,
}

const STATUS_TEXT: Record<State['kind'], string> = {
  loading: TEXT.loading,
  content: TEXT.connected,
  // The error is announced by the alert below, not by the status line.
  error: '',
}

type Props = {
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
}

export function StatusPage({ timeoutMs }: Props) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  // Each retry is a new attempt; the effect below runs once per attempt.
  const [attempt, setAttempt] = useState(0)
  // Always mounted, so a screen reader announces each change and the focus has where to go
  // when the retry button disappears.
  const statusLine = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    // Abandoned when the screen goes away or a new attempt starts, so no request is left
    // alive behind it.
    const abandon = new AbortController()
    void checkReadiness({ timeoutMs, signal: abandon.signal }).then((readiness) => {
      if (readiness.kind === 'cancelled') return
      setState(
        readiness.kind === 'ready' ? { kind: 'content' } : { kind: 'error', cause: readiness.kind },
      )
    })
    return () => abandon.abort()
  }, [attempt, timeoutMs])

  function retry() {
    setState({ kind: 'loading' })
    setAttempt((current) => current + 1)
    statusLine.current?.focus()
  }

  return (
    <Card aria-labelledby="status-heading">
      <CardTitle id="status-heading">{TEXT.heading}</CardTitle>
      <p
        ref={statusLine}
        role="status"
        tabIndex={-1}
        className={
          state.kind === 'content'
            ? 'flex items-center gap-2 font-semibold text-success outline-none'
            : 'text-sm text-muted-foreground outline-none'
        }
      >
        {state.kind === 'content' && <span aria-hidden="true" className="size-2 rounded-full bg-success" />}
        {STATUS_TEXT[state.kind]}
      </p>
      {state.kind === 'content' && <p className="text-sm text-muted-foreground">{TEXT.connectedDetail}</p>}
      {state.kind === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="font-semibold text-destructive">{TEXT.disconnected}</p>
          <p className="text-sm text-muted-foreground">{ERROR_MESSAGES[state.cause]}</p>
          <Button onClick={retry}>{MESSAGES.common.retry}</Button>
        </div>
      )}
    </Card>
  )
}
