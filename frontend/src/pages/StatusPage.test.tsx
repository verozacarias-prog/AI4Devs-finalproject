/**
 * Cases 35 to 39, 45 to 48 and 51: the states of the status page. The API is simulated at the network level,
 * so the page and its API call are tested together.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'
import { StatusPage } from './StatusPage'

const READYZ = '*/readyz'
const ready = () => HttpResponse.json({ status: 'ok' })
const databaseDown = () => HttpResponse.json({ status: 'unavailable' }, { status: 503 })
const apiDown = () => HttpResponse.error()

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

test('case 35: while the API is being asked, it says so', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(READYZ, async () => {
      await pending
      return ready()
    }),
  )

  render(<StatusPage />)

  expect(screen.getByRole('status').textContent).toBe('Consultando el estado…')
  answer()
  await screen.findByText('Todo conectado')
})

test('case 36: when the API reaches the database, everything is connected', async () => {
  api.use(http.get(READYZ, ready))

  render(<StatusPage />)

  await screen.findByText('Todo conectado')
  expect(screen.getByRole('status').textContent).toBe('Todo conectado')
  screen.getByText('El dashboard llega a la API, y la API a la base de datos.')
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case 37: when the API cannot reach the database, it is an error with a retry', async () => {
  api.use(http.get(READYZ, databaseDown))

  render(<StatusPage />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Sin conexión')
  expect(alert.textContent).toContain('La API responde, pero no llega a la base de datos.')
  screen.getByRole('button', { name: 'Reintentar' })
})

test('case 38: when the API cannot be reached, it is an error with a retry', async () => {
  api.use(http.get(READYZ, apiDown))

  render(<StatusPage />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Sin conexión')
  expect(alert.textContent).toContain('No se puede llegar a la API.')
  screen.getByRole('button', { name: 'Reintentar' })
})

test('case 39: retrying after an error asks again and ends connected', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(READYZ, async () => {
      await pending
      return ready()
    }),
  )
  // The handler added last runs first: the first request fails, the second one waits.
  api.use(http.get(READYZ, apiDown, { once: true }))

  render(<StatusPage />)
  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  retry.click()

  expect((await screen.findByRole('status')).textContent).toBe('Consultando el estado…')
  expect(screen.queryByRole('alert')).toBeNull()
  answer()
  await screen.findByText('Todo conectado')
})

const apiFails = (status: number) => () => new HttpResponse(null, { status })
const apiNeverAnswers = async () => {
  await delay('infinite')
  return ready()
}

test.each([500, 404])(
  'case 45: when the API answers with an unexpected error (%i), it says so',
  async (status) => {
    api.use(http.get(READYZ, apiFails(status)))

    render(<StatusPage />)

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('Sin conexión')
    expect(alert.textContent).toContain('La API respondió con un error.')
    screen.getByRole('button', { name: 'Reintentar' })
  },
)

test('case 46: when the API does not answer in time, it is an error with a retry', async () => {
  api.use(http.get(READYZ, apiNeverAnswers))

  render(<StatusPage timeoutMs={50} />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Sin conexión')
  expect(alert.textContent).toContain('La API no respondió a tiempo.')
  screen.getByRole('button', { name: 'Reintentar' })
})

test('case 47: retrying moves the focus to the status line instead of losing it', async () => {
  api.use(http.get(READYZ, apiNeverAnswers))
  api.use(http.get(READYZ, apiDown, { once: true }))

  render(<StatusPage />)
  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  retry.focus()
  expect(document.activeElement).toBe(retry)
  retry.click()

  await screen.findByText('Consultando el estado…')
  expect(document.activeElement).toBe(screen.getByRole('status'))
})

test('case 48: the status line is one fixed element across every state', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(READYZ, async () => {
      await pending
      return ready()
    }),
  )
  api.use(http.get(READYZ, apiDown, { once: true }))

  render(<StatusPage />)
  const whileLoading = screen.getByRole('status')

  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  expect(screen.getByRole('status')).toBe(whileLoading)

  retry.click()
  await screen.findByText('Consultando el estado…')
  expect(screen.getByRole('status')).toBe(whileLoading)

  answer()
  await screen.findByText('Todo conectado')
  expect(screen.getByRole('status')).toBe(whileLoading)
})

test('case 46: running out of time while reading the answer is also a timeout', async () => {
  const bodyThatNeverEnds = new ReadableStream({ start() {} })
  api.use(
    http.get(
      READYZ,
      () => new HttpResponse(bodyThatNeverEnds, { headers: { 'Content-Type': 'application/json' } }),
    ),
  )

  render(<StatusPage timeoutMs={50} />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('La API no respondió a tiempo.')
})

test('case 51: closing the screen cancels the request in progress', async () => {
  api.use(http.get(READYZ, apiNeverAnswers))
  // What the page hands to the browser with its request: the signal that cancels it. The
  // simulated API is not asked whether it noticed, because it does not always notice.
  const sent = vi.spyOn(globalThis, 'fetch')

  const { unmount } = render(<StatusPage />)
  await vi.waitFor(() => expect(sent).toHaveBeenCalledTimes(1))
  const signal = sent.mock.calls[0][1]?.signal
  expect(signal?.aborted).toBe(false)
  unmount()

  expect(signal?.aborted).toBe(true)
})
