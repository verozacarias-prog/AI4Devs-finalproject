import { useEffect, useRef, useState } from 'react'
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
  'api-error': TEXT.apiError,
  'api-timeout': TEXT.apiTimeout,
  'api-unreachable': TEXT.apiUnreachable,
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
    <section className="card" aria-labelledby="status-heading">
      <h2 id="status-heading" className="card__heading">
        {TEXT.heading}
      </h2>
      <p
        ref={statusLine}
        role="status"
        tabIndex={-1}
        className={state.kind === 'content' ? 'status status--ok' : 'card__text'}
      >
        {STATUS_TEXT[state.kind]}
      </p>
      {state.kind === 'content' && <p className="card__text">{TEXT.connectedDetail}</p>}
      {state.kind === 'error' && (
        <div role="alert">
          <p className="status status--error">{TEXT.disconnected}</p>
          <p className="card__text">{ERROR_MESSAGES[state.cause]}</p>
          <button type="button" className="button" onClick={retry}>
            {TEXT.retry}
          </button>
        </div>
      )}
    </section>
  )
}
