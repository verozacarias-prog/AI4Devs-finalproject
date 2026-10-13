import { useEffect, useRef, useState } from 'react'
import type { Failure } from '../api/request'
import { enterAs, loadEntry, logout, type DevUser, type SessionUser } from '../api/session'
import { SEED_TEST_DATA_COMMAND } from '../constants'
import { MESSAGES } from '../messages'

/**
 * The four states of a screen (docs/convenciones-de-desarrollo.md, section 2). With content
 * it is one of three things: the list to choose from, the user who is in, or the notice that
 * the entry is off.
 */
type State =
  | { kind: 'loading' }
  | { kind: 'choose'; users: DevUser[] }
  | { kind: 'signed-in'; user: SessionUser }
  | { kind: 'unavailable' }
  | { kind: 'empty' }
  | { kind: 'error'; cause: ErrorCause }

type ErrorCause = Exclude<Failure['kind'], 'cancelled'>

/** What the next attempt does before asking where the person stands. */
type Step = { kind: 'load' } | { kind: 'enter'; userId: string } | { kind: 'logout' }

const TEXT = MESSAGES.devEntry

const ERROR_MESSAGES: Record<ErrorCause, string> = {
  'api-error': TEXT.apiError,
  'api-timeout': TEXT.apiTimeout,
  'api-unreachable': TEXT.apiUnreachable,
}

type Props = {
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
}

export function DevEntryPage({ timeoutMs }: Props) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  // Each attempt runs the effect below once: the first load, a retry, entering or leaving.
  const [attempt, setAttempt] = useState<{ step: Step; number: number }>({
    step: { kind: 'load' },
    number: 0,
  })
  // Always mounted, so a screen reader announces each change and the focus has where to go
  // when the button that was pressed disappears.
  const statusLine = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    // Abandoned when the screen goes away or a new attempt starts.
    const abandon = new AbortController()
    const options = { timeoutMs, signal: abandon.signal }

    async function run(): Promise<State | null> {
      const { step } = attempt
      if (step.kind !== 'load') {
        const done = step.kind === 'enter' ? await enterAs(step.userId, options) : await logout(options)
        if (done.kind === 'cancelled') return null
        if (done.kind !== 'entered' && done.kind !== 'closed') {
          return { kind: 'error', cause: done.kind }
        }
      }
      const entry = await loadEntry(options)
      switch (entry.kind) {
        case 'cancelled':
          return null
        case 'signed-in':
        case 'unavailable':
          return entry
        case 'choose':
          return entry.users.length > 0 ? entry : { kind: 'empty' }
        default:
          return { kind: 'error', cause: entry.kind }
      }
    }

    void run().then((next) => {
      if (next !== null && !abandon.signal.aborted) setState(next)
    })
    return () => abandon.abort()
  }, [attempt, timeoutMs])

  function start(step: Step) {
    setState({ kind: 'loading' })
    setAttempt((current) => ({ step, number: current.number + 1 }))
    statusLine.current?.focus()
  }

  return (
    <section className="card" aria-labelledby="dev-entry-heading">
      <h2 id="dev-entry-heading" className="card__heading">
        {TEXT.heading}
      </h2>
      <p
        ref={statusLine}
        role="status"
        tabIndex={-1}
        className={state.kind === 'signed-in' ? 'status status--ok' : 'card__text'}
      >
        {statusText(state)}
      </p>
      {state.kind === 'choose' && (
        <ul className="choices">
          {state.users.map((user) => (
            <li key={user.id}>
              <button
                type="button"
                className="button"
                onClick={() => start({ kind: 'enter', userId: user.id })}
              >
                {TEXT.enterAs(user.name)}
              </button>
            </li>
          ))}
        </ul>
      )}
      {state.kind === 'signed-in' && (
        <>
          <p className="card__text">{TEXT.signedInDetail}</p>
          <button type="button" className="button" onClick={() => start({ kind: 'logout' })}>
            {TEXT.logout}
          </button>
        </>
      )}
      {state.kind === 'empty' && (
        <>
          <p className="card__text">{TEXT.emptyDetail}</p>
          <pre className="command">
            <code>{SEED_TEST_DATA_COMMAND}</code>
          </pre>
          <button type="button" className="button" onClick={() => start({ kind: 'load' })}>
            {TEXT.retry}
          </button>
        </>
      )}
      {state.kind === 'unavailable' && <p className="card__text">{TEXT.unavailableDetail}</p>}
      {state.kind === 'error' && (
        <div role="alert">
          <p className="status status--error">{TEXT.failed}</p>
          <p className="card__text">{ERROR_MESSAGES[state.cause]}</p>
          <button type="button" className="button" onClick={() => start({ kind: 'load' })}>
            {TEXT.retry}
          </button>
        </div>
      )}
    </section>
  )
}

function statusText(state: State): string {
  switch (state.kind) {
    case 'loading':
      return TEXT.loading
    case 'choose':
      return TEXT.choose
    case 'signed-in':
      return TEXT.signedInAs(state.user.name)
    case 'empty':
      return TEXT.empty
    case 'unavailable':
      return TEXT.unavailable
    case 'error':
      // The error is announced by the alert below, not by the status line.
      return ''
  }
}
