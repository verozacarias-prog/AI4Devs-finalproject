/**
 * Cases C1-11 to C1-22 of FEAT-002 (docs/features/FEAT-002/spec.md): the web chat. The whole
 * dashboard is rendered, with Lucía already in and the API simulated at the network level.
 * The chat asks for new messages ten times as often as it does for real: every 50 ms while it
 * waits for a reply instead of every half second, and every 300 ms instead of every 3 seconds.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'
import App from '../App'

const INTERVAL = vi.hoisted(() => ({ waitingMs: 50, normalMs: 300 }))

vi.mock('../constants', async (original) => ({
  ...(await original<object>()),
  CHAT_WAITING_POLL_MS: INTERVAL.waitingMs,
  CHAT_POLL_MS: INTERVAL.normalMs,
}))

/** One and two seconds of the cases, at the same scale as the intervals. */
const ONE_SECOND_MS = 100
const TWO_SECONDS_MS = 200
/** Several of the longer intervals, for a screen that should no longer ask. */
const SEVERAL_INTERVALS_MS = 3 * INTERVAL.normalMs

const CHAT = '*/chat/messages'
const LUCIA = { id: '4379d06b-46d3-4f2e-a59e-addcb32388f8', name: 'Lucía' }
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/

type Message = {
  id: string
  direction: 'inbound' | 'outbound'
  text: string
  quoted_message_id: null
  response_kind: 'fixed_text' | null
  created_at: string
}

const fromLucia = (id: string, text: string, created_at: string): Message => ({
  id,
  direction: 'inbound',
  text,
  quoted_message_id: null,
  response_kind: null,
  created_at,
})

const fromPlatita = (id: string, text: string, created_at: string): Message => ({
  id,
  direction: 'outbound',
  text,
  quoted_message_id: null,
  response_kind: 'fixed_text',
  created_at,
})

const SUPERMARKET = fromLucia('im1', 'gasté 3500 en el súper', '2026-10-15T14:58:00-03:00')
const REPLY = fromPlatita('om1', 'Recibí tu mensaje. Todavía no puedo procesarlo.', '2026-10-15T14:58:04-03:00')

const conversation = (messages: Message[], next_cursor: string | null) => HttpResponse.json({ messages, next_cursor })

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

/** An API where Lucía is in. The chat answers with the handler of each case. */
function apiWithLuciaIn(...chat: Parameters<typeof api.use>) {
  api.use(
    http.get('*/healthz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/readyz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/me', () => HttpResponse.json(LUCIA)),
    http.get('*/accounts', () => HttpResponse.json({ accounts: [] })),
    ...chat,
  )
}

/** Renders the dashboard and opens the chat from the menu. */
async function openChat(): Promise<HTMLElement> {
  render(<App />)
  const nav = await screen.findByRole('navigation', { name: 'Menú principal' })
  const chat = await within(nav).findByRole('button', { name: 'Chat' })
  fireEvent.click(chat)
  return nav
}

/** The messages of the conversation, each as "side · text · time", read as a person would. */
function messagesShown(): string[] {
  const log = screen.getByRole('log', { name: 'Conversación con Platita' })
  return within(log)
    .getAllByRole('listitem')
    .map((item) => {
      const side = item.classList.contains('chat__message--mine') ? 'right' : 'left'
      return `${side} · ${(item.textContent ?? '').trim()}`
    })
}

test('case C1-11: while the conversation opens, it says so and there is nowhere to write', async () => {
  let reads = 0
  apiWithLuciaIn(
    http.get(CHAT, async () => {
      reads += 1
      // The first read is the dashboard asking whether the chat is on; the screen waits forever.
      if (reads > 1) await delay('infinite')
      return conversation([], null)
    }),
  )

  await openChat()

  await screen.findByText('Abriendo la conversación…')
  expect(screen.queryByRole('log')).toBeNull()
  expect(screen.queryByLabelText('Tu mensaje')).toBeNull()
})

test('case C1-12: the conversation of Lucía, each message on its side and with its time', async () => {
  apiWithLuciaIn(http.get(CHAT, () => conversation([SUPERMARKET, REPLY], 'om1')))

  await openChat()

  await screen.findByText('gasté 3500 en el súper')
  expect(messagesShown()).toEqual([
    'right · Vos: gasté 3500 en el súper14:58',
    'left · Platita: Recibí tu mensaje. Todavía no puedo procesarlo.14:58',
  ])
})

test('case C1-13: with no reply to the last message, Platita is processing', async () => {
  apiWithLuciaIn(http.get(CHAT, () => conversation([SUPERMARKET], 'im1')))

  await openChat()

  await screen.findByText('gasté 3500 en el súper')
  screen.getByText('Platita está procesando…')
})

test('case C1-14: write and send with Enter', async () => {
  const sent: { text: unknown; key: string | null }[] = []
  apiWithLuciaIn(
    http.get(CHAT, () => conversation([], null)),
    http.post(CHAT, async ({ request }) => {
      const body = (await request.json()) as { text: unknown }
      sent.push({ text: body.text, key: request.headers.get('Idempotency-Key') })
      return HttpResponse.json({ id: 'im1', status: 'pending' }, { status: 202 })
    }),
  )
  await openChat()
  const input = await screen.findByLabelText('Tu mensaje')

  fireEvent.change(input, { target: { value: 'gasté 3500 en el súper' } })
  fireEvent.keyDown(input, { key: 'Enter' })

  await waitFor(() => expect(sent).toHaveLength(1))
  expect(sent[0].text).toBe('gasté 3500 en el súper')
  expect(sent[0].key).toMatch(UUID)
  expect(messagesShown()).toEqual(['right · Vos: gasté 3500 en el súper'])
  expect((input as HTMLTextAreaElement).value).toBe('')
  screen.getByText('Platita está procesando…')
})

test('case C1-15: the reply shows up by itself, asking from the last message', async () => {
  const cursors: (string | null)[] = []
  apiWithLuciaIn(
    http.get(CHAT, ({ request }) => {
      const after = new URL(request.url).searchParams.get('after')
      cursors.push(after)
      if (after === 'im1') return conversation([REPLY], 'om1')
      if (after === 'om1') return conversation([], 'om1')
      return conversation([SUPERMARKET], 'im1')
    }),
  )

  await openChat()

  await screen.findByText('Recibí tu mensaje. Todavía no puedo procesarlo.')
  expect(cursors).toContain('im1')
  expect(messagesShown()).toEqual([
    'right · Vos: gasté 3500 en el súper14:58',
    'left · Platita: Recibí tu mensaje. Todavía no puedo procesarlo.14:58',
  ])
  expect(screen.queryByText('Platita está procesando…')).toBeNull()
})

test('case C1-16: with another screen open, it does not ask', async () => {
  let polls = 0
  apiWithLuciaIn(
    http.get(CHAT, ({ request }) => {
      if (new URL(request.url).searchParams.has('after')) polls += 1
      return conversation([SUPERMARKET, REPLY], 'om1')
    }),
  )
  const nav = await openChat()
  await waitFor(() => expect(polls).toBeGreaterThan(0))

  fireEvent.click(within(nav).getByRole('button', { name: 'Cuentas' }))
  await screen.findByRole('heading', { name: 'Tus cuentas' })
  const pollsWhenLeaving = polls
  await new Promise((resolve) => setTimeout(resolve, SEVERAL_INTERVALS_MS))

  expect(polls).toBe(pollsWhenLeaving)
})

test('case C1-17: a message with tags is shown as text', async () => {
  const tagged = '<script>alert(1)</script><b>hola</b>'
  apiWithLuciaIn(http.get(CHAT, () => conversation([fromPlatita('om1', tagged, '2026-10-15T14:58:04-03:00')], 'om1')))

  await openChat()

  const shown = await screen.findByText(tagged)
  expect(shown.querySelector('script')).toBeNull()
  expect(shown.querySelector('b')).toBeNull()
  expect(document.querySelector('script')).toBeNull()
})

test('case C1-18: with the chat on, the menu leads to the conversation', async () => {
  apiWithLuciaIn(http.get(CHAT, () => conversation([], null)))
  render(<App />)
  const nav = await screen.findByRole('navigation', { name: 'Menú principal' })
  const chat = await within(nav).findByRole('button', { name: 'Chat' })

  const testing = within(nav).getByRole('list', { name: 'Pruebas' })
  expect(within(testing).getAllByRole('button').map((option) => option.textContent)).toEqual([
    'Chat',
    'Estado del sistema',
  ])
  fireEvent.click(chat)

  await screen.findByRole('heading', { name: 'Chat con Platita' })
  expect(within(nav).getByRole('button', { name: 'Chat' }).getAttribute('aria-current')).toBe('page')
})

/** An API whose conversation is always the same, and which counts the reads for new messages. */
function countingPolls(messages: Message[], cursor: string): { polls: number } {
  const counted = { polls: 0 }
  apiWithLuciaIn(
    http.get(CHAT, ({ request }) => {
      if (new URL(request.url).searchParams.has('after')) counted.polls += 1
      return conversation(new URL(request.url).searchParams.has('after') ? [] : messages, cursor)
    }),
  )
  return counted
}

test('case C1-19: while it waits for a reply, it asks every half second', async () => {
  const counted = countingPolls([SUPERMARKET], 'im1')
  await openChat()
  await screen.findByText('gasté 3500 en el súper')

  await new Promise((resolve) => setTimeout(resolve, TWO_SECONDS_MS))

  expect(counted.polls).toBeGreaterThanOrEqual(3)
})

test('case C1-20: with the conversation answered, it asks every 3 seconds', async () => {
  const counted = countingPolls([SUPERMARKET, REPLY], 'om1')
  await openChat()
  await screen.findByText('Recibí tu mensaje. Todavía no puedo procesarlo.')

  await new Promise((resolve) => setTimeout(resolve, TWO_SECONDS_MS))

  expect(counted.polls).toBe(0)
})

test('case C1-21: writing in an answered conversation brings the next read forward', async () => {
  const polledAt: number[] = []
  apiWithLuciaIn(
    http.get(CHAT, ({ request }) => {
      const asksForNew = new URL(request.url).searchParams.has('after')
      if (asksForNew) polledAt.push(performance.now())
      return conversation(asksForNew ? [] : [SUPERMARKET, REPLY], 'om1')
    }),
    http.post(CHAT, () => HttpResponse.json({ id: 'im2', status: 'pending' }, { status: 202 })),
  )
  await openChat()
  const input = await screen.findByLabelText('Tu mensaje')
  // Right after a read, so the next one, every 3 seconds, is as far as it gets.
  await waitFor(() => expect(polledAt.length).toBeGreaterThan(0))

  const sentAt = performance.now()
  fireEvent.change(input, { target: { value: 'y 1200 de nafta' } })
  fireEvent.keyDown(input, { key: 'Enter' })
  await new Promise((resolve) => setTimeout(resolve, ONE_SECOND_MS))

  expect(polledAt.some((at) => at > sentAt)).toBe(true)
})

test('case C1-22: the message a read brought before the send answered is shown once', async () => {
  let posted = false
  let postAnswered = false
  let readBroughtIt: () => void = () => {}
  const broughtByARead = new Promise<void>((resolve) => {
    readBroughtIt = resolve
  })
  apiWithLuciaIn(
    http.get(CHAT, ({ request }) => {
      const after = new URL(request.url).searchParams.get('after')
      if (after === 'im1') return postAnswered ? conversation([REPLY], 'om1') : conversation([], 'im1')
      if (after === 'om1') return conversation([], 'om1')
      if (!posted) return conversation([], null)
      readBroughtIt()
      return conversation([SUPERMARKET], 'im1')
    }),
    http.post(CHAT, async () => {
      posted = true
      await broughtByARead
      postAnswered = true
      return HttpResponse.json({ id: 'im1', status: 'pending' }, { status: 202 })
    }),
  )
  await openChat()
  const input = await screen.findByLabelText('Tu mensaje')

  fireEvent.change(input, { target: { value: 'gasté 3500 en el súper' } })
  fireEvent.keyDown(input, { key: 'Enter' })

  await screen.findByText('Recibí tu mensaje. Todavía no puedo procesarlo.')
  expect(screen.getAllByText('gasté 3500 en el súper')).toHaveLength(1)
  await waitFor(() => expect(screen.queryByText('Platita está procesando…')).toBeNull())
})
