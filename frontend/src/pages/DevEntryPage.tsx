import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import type { Failure } from '../api/request'
import {
  enterAs,
  enterWithLink,
  loadEntry,
  logout,
  type DevUser,
  type SessionUser,
} from '../api/session'
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
  | { kind: 'error'; cause: ErrorCause; retry: Step }
  /** A personal link opened for the first time: the test notice waits to be accepted. */
  | { kind: 'notice'; value: string; version: string }
  | { kind: 'link-rejected' }

type ErrorCause = Exclude<Failure['kind'], 'cancelled'>

/** What the next attempt does before asking where the person stands. */
type Step =
  | { kind: 'load' }
  | { kind: 'enter'; userId: string }
  | { kind: 'link'; value: string; acceptedNotice: string | null }
  | { kind: 'logout' }

/** The value of a personal link: it travels in the fragment, which never reaches the server. */
function linkInTheAddress(): string | null {
  return window.location.hash.slice(1) || null
}

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
  const [link] = useState(linkInTheAddress)
  // Until the first answer nobody knows whether this entry exists here: only the status line
  // shows, and the card is never drawn in an environment without it.
  const [answered, setAnswered] = useState(false)
  // Each attempt runs the effect below once: the first load, a retry, entering or leaving.
  const [attempt, setAttempt] = useState<{ step: Step; number: number }>({
    step: link === null ? { kind: 'load' } : { kind: 'link', value: link, acceptedNotice: null },
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

  // Out of the address bar before any answer: nobody should see it or copy it by accident.
  useEffect(() => {
    if (link !== null) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }
  }, [link])

  useEffect(() => {
    // Abandoned when the screen goes away or a new attempt starts.
    const abandon = new AbortController()
    const options = { timeoutMs, signal: abandon.signal }

    async function run(): Promise<State | null> {
      const { step } = attempt
      // Only the link goes again as it was: its value is not in the address any more.
      const retry: Step = step.kind === 'link' ? step : { kind: 'load' }
      if (step.kind === 'link') {
        const done = await enterWithLink(step.value, step.acceptedNotice, options)
        if (done.kind === 'cancelled') return null
        if (done.kind === 'link-rejected') return done
        if (done.kind === 'notice-required') {
          return { kind: 'notice', value: step.value, version: done.version }
        }
        if (done.kind !== 'entered') return { kind: 'error', cause: done.kind, retry }
      } else if (step.kind !== 'load') {
        const done = step.kind === 'enter' ? await enterAs(step.userId, options) : await logout(options)
        if (done.kind === 'cancelled') return null
        if (done.kind !== 'entered' && done.kind !== 'closed') {
          return { kind: 'error', cause: done.kind, retry }
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
          return { kind: 'error', cause: entry.kind, retry }
      }
    }

    void run().then((next) => {
      if (next === null || abandon.signal.aborted) return
      setState(next)
      setAnswered(true)
      // An error says nothing about the session, so it changes nothing outside.
      if (next.kind === 'signed-in' || next.kind === 'choose' || next.kind === 'empty' || next.kind === 'unavailable') {
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
    <Card
      aria-labelledby={answered ? 'dev-entry-heading' : undefined}
      className={answered ? undefined : 'border-0 bg-transparent p-0 shadow-none'}
    >
      {answered && (
        <CardTitle id="dev-entry-heading">
          {state.kind === 'notice' ? TEXT.noticeHeading : link === null ? TEXT.heading : TEXT.linkHeading}
        </CardTitle>
      )}
      <p
        ref={statusLine}
        role="status"
        tabIndex={-1}
        className={
          state.kind === 'signed-in'
            ? 'font-semibold text-success outline-none'
            : 'text-sm text-muted-foreground outline-none'
        }
      >
        {statusText(state)}
      </p>
      {state.kind === 'notice' && (
        <div className="flex flex-col items-start gap-2">
          <ul className="list-disc pl-5 text-sm">
            {TEXT.noticePoints.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
          <Button
            onClick={() => start({ kind: 'link', value: state.value, acceptedNotice: state.version })}
          >
            {TEXT.accept}
          </Button>
        </div>
      )}
      {state.kind === 'link-rejected' && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="font-semibold text-destructive">{TEXT.linkRejected}</p>
          <p className="text-sm text-muted-foreground">{TEXT.linkRejectedDetail}</p>
        </div>
      )}
      {state.kind === 'choose' && (
        <ul className="flex flex-wrap gap-2">
          {state.users.map((user) => (
            <li key={user.id}>
              <Button variant="outline" onClick={() => start({ kind: 'enter', userId: user.id })}>
                {TEXT.enterAs(user.name)}
              </Button>
            </li>
          ))}
        </ul>
      )}
      {state.kind === 'signed-in' && (
        <div className="flex flex-col items-start gap-2">
          <p className="text-sm text-muted-foreground">{TEXT.signedInDetail}</p>
          <Button variant="outline" onClick={() => start({ kind: 'logout' })}>
            {TEXT.logout}
          </Button>
        </div>
      )}
      {state.kind === 'empty' && (
        <div className="flex flex-col items-start gap-2">
          <p className="text-sm text-muted-foreground">{TEXT.emptyDetail}</p>
          <pre className="w-full overflow-x-auto rounded-md border bg-muted p-3 font-mono text-sm">
            <code>{SEED_TEST_DATA_COMMAND}</code>
          </pre>
          <Button onClick={() => start({ kind: 'load' })}>{MESSAGES.common.retry}</Button>
        </div>
      )}
      {state.kind === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="font-semibold text-destructive">{TEXT.failed}</p>
          <p className="text-sm text-muted-foreground">{ERROR_MESSAGES[state.cause]}</p>
          <Button onClick={() => start(state.retry)}>{MESSAGES.common.retry}</Button>
        </div>
      )}
    </Card>
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
    case 'notice':
      return TEXT.noticeAnnounced
    case 'error':
    case 'link-rejected':
      // The error is announced by the alert below, not by the status line.
      return ''
  }
}
