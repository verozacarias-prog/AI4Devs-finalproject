import { useEffect, useState } from 'react'
import { checkReadiness, type Readiness } from '../api/health'
import { MESSAGES } from '../messages'

/**
 * The three states of this screen. It shows no user data, so it has no empty state
 * (docs/convenciones-de-desarrollo.md, section 2).
 */
type State = { kind: 'loading' } | { kind: 'content' } | { kind: 'error'; cause: ErrorCause }

type ErrorCause = Exclude<Readiness['kind'], 'ready'>

const TEXT = MESSAGES.status

const ERROR_MESSAGES: Record<ErrorCause, string> = {
  'database-unreachable': TEXT.databaseUnreachable,
  'api-unreachable': TEXT.apiUnreachable,
}

export function StatusPage() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  // Each retry is a new attempt; the effect below runs once per attempt.
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    void checkReadiness().then((readiness) => {
      if (cancelled) return
      setState(
        readiness.kind === 'ready' ? { kind: 'content' } : { kind: 'error', cause: readiness.kind },
      )
    })
    return () => {
      cancelled = true
    }
  }, [attempt])

  function retry() {
    setState({ kind: 'loading' })
    setAttempt((current) => current + 1)
  }

  return (
    <section className="card" aria-labelledby="status-heading">
      <h2 id="status-heading" className="card__heading">
        {TEXT.heading}
      </h2>
      {state.kind === 'loading' && (
        <p className="card__text" role="status">
          {TEXT.loading}
        </p>
      )}
      {state.kind === 'content' && (
        <>
          <p className="status status--ok" role="status">
            {TEXT.connected}
          </p>
          <p className="card__text">{TEXT.connectedDetail}</p>
        </>
      )}
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
