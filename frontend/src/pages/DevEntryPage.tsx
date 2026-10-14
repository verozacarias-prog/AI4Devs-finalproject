import { useEffect, useRef, useState } from 'react'
import type { Failure } from '../api/request'
import { enterAs, loadEntry, logout, type DevUser, type SessionUser } from '../api/session'
import { SEED_TEST_DATA_COMMAND } from '../constants'
import { MESSAGES } from '../messages'

/**
 * The four states of a screen (docs/convenciones-de-desarrollo.md, section 2). With content
 * it is the list to choose from or the user who is in. With the entry off there is nothing
 * to show: the card is not there, so that nobody outside development ever sees it.
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

const ERROR_MESSAGES: Record<ErrorCause, string> = MESSAGES.common.apiFailures

type Props = {
  /** Told who is in once the screen knows it, or null when nobody is. */
  onSessionChange?: (user: SessionUser | null) => void
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
}

export function DevEntryPage({ onSessionChange, timeoutMs }: Props) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  // Each attempt runs the effect below once: the first load, a retry, entering or leaving.
  const [attempt, setAttempt] = useState<{ step: Step; number: number }>({
    step: { kind: 'load' },
    number: 0,
  })
  // Always mounted, so a screen reader announces each change and the focus has where to go
  // when the button that was pressed disappears.
  const statusLine = useRef<HTMLParagraphElement>(null)
  // Read when an answer arrives, so a new callback does not start a new attempt.
  const sessionListener = useRef(onSessionChange)
  useEffect(() => {
    sessionListener.current = onSessionChange
  }, [onSessionChange])

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
      if (next === null || abandon.signal.aborted) return
      setState(next)
      // An error says nothing about the session, so it changes nothing outside.
      if (next.kind !== 'error' && next.kind !== 'loading') {
        sessionListener.current?.(next.kind === 'signed-in' ? next.user : null)
      }
    })
    return () => abandon.abort()
  }, [attempt, timeoutMs])

  function start(step: Step) {
    setState({ kind: 'loading' })
    setAttempt((current) => ({ step, number: current.number + 1 }))
    statusLine.current?.focus()
  }

  if (state.kind === 'unavailable') return null

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
            {MESSAGES.common.retry}
          </button>
        </>
      )}
      {state.kind === 'error' && (
        <div role="alert">
          <p className="status status--error">{TEXT.failed}</p>
          <p className="card__text">{ERROR_MESSAGES[state.cause]}</p>
          <button type="button" className="button" onClick={() => start({ kind: 'load' })}>
            {MESSAGES.common.retry}
          </button>
        </div>
      )}
    </section>
  )
}

function statusText(state: Exclude<State, { kind: 'unavailable' }>): string {
  switch (state.kind) {
    case 'loading':
      return TEXT.loading
    case 'choose':
      return TEXT.choose
    case 'signed-in':
      return TEXT.signedInAs(state.user.name)
    case 'empty':
      return TEXT.empty
    case 'error':
      // The error is announced by the alert below, not by the status line.
      return ''
  }
}
