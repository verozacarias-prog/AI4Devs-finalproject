import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/class-names'
import { loadConversation, sendMessage, type ChatMessage } from '../api/chat'
import type { Failure } from '../api/request'
import { CHAT_POLL_MS, ISO_TIME_END, ISO_TIME_START } from '../constants'
import { MESSAGES } from '../messages'

/**
 * The web chat (FEAT-002): what the user writes goes to the API, and the replies of Platita
 * arrive by asking every few seconds, while this screen is open. The four states of a screen
 * are about the first read of the conversation (docs/convenciones-de-desarrollo.md, section 2).
 * What Platita and the user wrote is always shown as text, never as HTML (ADR 0016).
 */
type State = { kind: 'loading' } | { kind: 'ready' } | { kind: 'error'; cause: ErrorCause }

type ErrorCause = Exclude<Failure['kind'], 'cancelled'>

/** A message written here that the conversation does not bring yet. */
type Outgoing = {
  /** The Idempotency-Key: the same one on every retry, so it is never stored twice. */
  key: string
  text: string
  status: 'sending' | 'sent' | 'failed'
  /** The id the API gave it, to know when the conversation brings it. */
  id?: string
}

const TEXT = MESSAGES.chat

const ERROR_MESSAGES: Record<ErrorCause, string> = MESSAGES.common.apiFailures

type Props = {
  /** Called when the API says there is no session: the entry is shown again. */
  onNoSession: () => void
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
  /** How often to ask for new messages. Tests pass a short one. */
  pollMs?: number
}

export function ChatPage({ onNoSession, timeoutMs, pollMs = CHAT_POLL_MS }: Props) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [outgoing, setOutgoing] = useState<Outgoing[]>([])
  const [pollFailed, setPollFailed] = useState(false)
  const [draft, setDraft] = useState('')
  // Where the next read starts. A ref, so the polling does not start over with each answer.
  const cursor = useRef<string | null>(null)
  const statusLine = useRef<HTMLParagraphElement>(null)

  const arrived = useCallback((loaded: ChatMessage[]) => {
    if (loaded.length === 0) return
    setMessages((current) => {
      const known = new Set(current.map((message) => message.id))
      return [...current, ...loaded.filter((message) => !known.has(message.id))]
    })
    const ids = new Set(loaded.map((message) => message.id))
    setOutgoing((current) => current.filter((message) => message.id === undefined || !ids.has(message.id)))
  }, [])

  // The first read of the conversation.
  useEffect(() => {
    const abandon = new AbortController()
    void loadConversation(null, { timeoutMs, signal: abandon.signal }).then((loaded) => {
      if (abandon.signal.aborted || loaded.kind === 'cancelled') return
      if (loaded.kind === 'no-session') {
        onNoSession()
        return
      }
      if (loaded.kind !== 'loaded') {
        setState({ kind: 'error', cause: loaded.kind === 'disabled' ? 'api-error' : loaded.kind })
        return
      }
      cursor.current = loaded.nextCursor
      setMessages(loaded.messages)
      setState({ kind: 'ready' })
    })
    return () => abandon.abort()
  }, [attempt, timeoutMs, onNoSession])

  // The read it repeats while the screen is open. Each one starts when the previous ended.
  useEffect(() => {
    if (state.kind !== 'ready') return
    const abandon = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const ask = () => {
      void loadConversation(cursor.current, { timeoutMs, signal: abandon.signal }).then((loaded) => {
        if (abandon.signal.aborted || loaded.kind === 'cancelled') return
        if (loaded.kind === 'no-session') {
          onNoSession()
          return
        }
        if (loaded.kind === 'loaded') {
          cursor.current = loaded.nextCursor
          arrived(loaded.messages)
          setPollFailed(false)
        } else {
          setPollFailed(true)
        }
        timer = setTimeout(ask, pollMs)
      })
    }
    timer = setTimeout(ask, pollMs)
    return () => {
      abandon.abort()
      clearTimeout(timer)
    }
  }, [state.kind, timeoutMs, pollMs, onNoSession, arrived])

  const deliver = useCallback(
    (message: Outgoing) => {
      void sendMessage(message.text, message.key, { timeoutMs }).then((sent) => {
        if (sent.kind === 'cancelled') return
        if (sent.kind === 'no-session') {
          onNoSession()
          return
        }
        setOutgoing((current) =>
          current.map((candidate) =>
            candidate.key !== message.key
              ? candidate
              : sent.kind === 'sent'
                ? { ...candidate, status: 'sent', id: sent.id }
                : { ...candidate, status: 'failed' },
          ),
        )
      })
    },
    [timeoutMs, onNoSession],
  )

  function send(event?: FormEvent) {
    event?.preventDefault()
    const text = draft.trim()
    if (text === '') return
    const message: Outgoing = { key: crypto.randomUUID(), text, status: 'sending' }
    setOutgoing((current) => [...current, message])
    setDraft('')
    deliver(message)
  }

  function resend(message: Outgoing) {
    const again: Outgoing = { ...message, status: 'sending' }
    setOutgoing((current) => current.map((candidate) => (candidate.key === message.key ? again : candidate)))
    deliver(again)
  }

  function sendOnEnter(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, as in WhatsApp; Shift and Enter starts a new line.
    if (event.key === 'Enter' && !event.shiftKey) send(event)
  }

  function retry() {
    setState({ kind: 'loading' })
    setAttempt((current) => current + 1)
    statusLine.current?.focus()
  }

  const ready = state.kind === 'ready'
  const empty = ready && messages.length === 0 && outgoing.length === 0
  const lastMessage = messages.at(-1)
  const processing =
    ready &&
    (outgoing.some((message) => message.status !== 'failed') ||
      (outgoing.length === 0 && lastMessage?.direction === 'inbound'))

  return (
    <Card aria-labelledby="chat-heading">
      <CardTitle id="chat-heading" className="text-xl">
        {TEXT.heading}
      </CardTitle>
      <p ref={statusLine} role="status" tabIndex={-1} className="text-sm text-muted-foreground outline-none empty:hidden">
        {state.kind === 'loading' ? TEXT.loading : empty ? TEXT.empty : processing ? TEXT.processing : ''}
      </p>
      {empty && <CardDescription>{TEXT.emptyDetail}</CardDescription>}
      {ready && !empty && (
        <ol aria-label={TEXT.conversation} role="log" className="flex flex-col gap-2">
          {messages.map((message) => (
            <Bubble key={message.id} mine={message.direction === 'inbound'} time={timeOf(message.created_at)}>
              {message.text}
            </Bubble>
          ))}
          {outgoing.map((message) => (
            <Bubble
              key={message.key}
              mine
              time={null}
              footer={
                message.status === 'failed' && (
                  <span className="chat__not-sent mt-2 flex items-center justify-end gap-2 self-end rounded-md bg-card px-2 py-1 text-xs">
                    <span className="font-semibold text-destructive">{TEXT.notSent}</span>
                    <Button size="sm" variant="outline" className="text-foreground" onClick={() => resend(message)}>
                      {MESSAGES.common.retry}
                    </Button>
                  </span>
                )
              }
            >
              {message.text}
            </Bubble>
          ))}
        </ol>
      )}
      {ready && pollFailed && <p className="text-sm text-destructive">{TEXT.pollFailed}</p>}
      {ready && (
        <form onSubmit={send} className="flex items-end gap-2">
          <label htmlFor="chat-input" className="sr-only">
            {TEXT.inputLabel}
          </label>
          <textarea
            id="chat-input"
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={sendOnEnter}
            className="min-h-10 flex-1 resize-none rounded-md border border-input bg-card px-3 py-2 text-sm outline-none focus-visible:ring-(length:--focus-ring-width) focus-visible:ring-ring"
          />
          <Button type="submit" disabled={draft.trim() === ''}>
            {TEXT.send}
          </Button>
        </form>
      )}
      {state.kind === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="font-semibold text-destructive">{TEXT.failed}</p>
          <p className="text-sm text-muted-foreground">{ERROR_MESSAGES[state.cause]}</p>
          <Button onClick={retry}>{MESSAGES.common.retry}</Button>
        </div>
      )}
    </Card>
  )
}

/**
 * One message, on the side of who wrote it, with its time. Who wrote it is also said in words,
 * for whoever does not see the side or the colour. The `chat…` class names have no style of
 * their own: the tests of this screen find a message by them. Do not remove them as unused.
 */
function Bubble({
  mine,
  time,
  footer,
  children,
}: {
  mine: boolean
  time: string | null
  footer?: ReactNode
  children: string
}) {
  return (
    <li
      className={cn(
        'chat__message flex max-w-[80%] flex-col rounded-lg px-3 py-2 text-sm',
        mine
          ? 'chat__message--mine self-end bg-primary text-primary-foreground'
          : 'chat__message--platita self-start bg-muted text-foreground',
      )}
    >
      <span className="sr-only">{mine ? TEXT.authorUser : TEXT.authorPlatita}: </span>
      <span className="chat__text whitespace-pre-wrap">{children}</span>
      {time !== null && (
        <span className={cn('mt-1 self-end text-xs', mine ? 'text-primary-foreground/80' : 'text-muted-foreground')}>
          {time}
        </span>
      )}
      {footer}
    </li>
  )
}

/** The hour and minute of a message, as the API wrote it: already in the time zone of the user. */
function timeOf(createdAt: string): string {
  return createdAt.slice(ISO_TIME_START, ISO_TIME_END)
}
