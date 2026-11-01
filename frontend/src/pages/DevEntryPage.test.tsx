/**
 * Cases 55 to 67: the states of the development entry. The API is simulated at the network
 * level, so the page and its API calls are tested together.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'
import { DevEntryPage } from './DevEntryPage'

const ME = '*/me'
const USERS = '*/dev/users'
const SESSION = '*/dev/session'
const LOGOUT = '*/auth/logout'

const LUCIA = { id: crypto.randomUUID(), name: 'Lucía' }
const PABLO = { id: crypto.randomUUID(), name: 'Pablo' }
const SOFIA = { id: crypto.randomUUID(), name: 'Sofía' }

const noSession = () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
const sessionOf = (user: typeof LUCIA) => () => HttpResponse.json(user)
const usersAre = (users: (typeof LUCIA)[]) => () => HttpResponse.json({ users })
const noContent = () => new HttpResponse(null, { status: 204 })
const notFound = () => HttpResponse.json({ error: 'not_found' }, { status: 404 })
const internalError = () => HttpResponse.json({ error: 'internal_error' }, { status: 500 })
const apiDown = () => HttpResponse.error()
const neverAnswers = async () => {
  await delay('infinite')
  return noSession()
}

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

/** An API where nobody is in until someone enters, and nobody is in again after leaving. */
function apiWithTheThreeUsers() {
  let current: typeof LUCIA | null = null
  const calls: { path: string; contentType: string | null; body: unknown }[] = []
  const all = [LUCIA, PABLO, SOFIA]
  api.use(
    http.get(ME, () => (current ? HttpResponse.json(current) : noSession())),
    http.get(USERS, usersAre(all)),
    http.post(SESSION, async ({ request }) => {
      const body = (await request.json()) as { user_id: string }
      calls.push({ path: 'session', contentType: request.headers.get('Content-Type'), body })
      current = all.find((user) => user.id === body.user_id) ?? null
      return current ? noContent() : notFound()
    }),
    http.post(LOGOUT, async ({ request }) => {
      calls.push({
        path: 'logout',
        contentType: request.headers.get('Content-Type'),
        body: await request.json(),
      })
      current = null
      return noContent()
    }),
  )
  return calls
}

test('case 55: while the API is being asked, it says so', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(ME, async () => {
      await pending
      return sessionOf(LUCIA)()
    }),
  )

  render(<DevEntryPage />)

  expect(screen.getByRole('status').textContent).toBe('Consultando la sesión…')
  answer()
  await screen.findByText('Entraste como Lucía')
})

test('case 56: without a session, it lists the test users in the order they arrive', async () => {
  api.use(http.get(ME, noSession), http.get(USERS, usersAre([LUCIA, PABLO, SOFIA])))

  render(<DevEntryPage />)

  await screen.findByText('Elegí con qué usuario de prueba entrar.')
  expect(screen.getAllByRole('button').map((button) => button.textContent)).toEqual([
    'Entrar como Lucía',
    'Entrar como Pablo',
    'Entrar como Sofía',
  ])
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case 57: choosing a user opens the session and says who is in', async () => {
  const calls = apiWithTheThreeUsers()

  render(<DevEntryPage />)
  ;(await screen.findByRole('button', { name: 'Entrar como Lucía' })).click()

  await screen.findByText('Entraste como Lucía')
  expect(screen.getByRole('status').textContent).toBe('Entraste como Lucía')
  screen.getByRole('button', { name: 'Cerrar sesión' })
  expect(screen.queryByRole('button', { name: 'Entrar como Pablo' })).toBeNull()
  expect(calls.map((call) => [call.path, call.body])).toEqual([
    ['session', { user_id: LUCIA.id }],
  ])
})

test('case 58: with a session already open, it says who is in without asking for the list', async () => {
  // No handler for the list: asking for it would fail the test.
  api.use(http.get(ME, sessionOf(PABLO)))

  render(<DevEntryPage />)

  await screen.findByText('Entraste como Pablo')
  screen.getByRole('button', { name: 'Cerrar sesión' })
})

test('case 59: closing the session goes back to the list', async () => {
  const calls = apiWithTheThreeUsers()

  render(<DevEntryPage />)
  ;(await screen.findByRole('button', { name: 'Entrar como Sofía' })).click()
  ;(await screen.findByRole('button', { name: 'Cerrar sesión' })).click()

  await screen.findByRole('button', { name: 'Entrar como Lucía' })
  expect(screen.queryByText('Entraste como Sofía')).toBeNull()
  expect(calls.map((call) => call.path)).toEqual(['session', 'logout'])
})

test('case 60: without test users it is empty, with the command to create them', async () => {
  api.use(http.get(ME, noSession), http.get(USERS, usersAre([])))

  render(<DevEntryPage />)

  await screen.findByText('No hay usuarios de prueba')
  screen.getByText('docker compose exec api python -m app.adapters.inbound.operator_commands.seed_test_data')
  screen.getByRole('button', { name: 'Reintentar' })
  // Empty is not an error.
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case 61: with the entry off, the card is not shown at all', async () => {
  let asked = false
  api.use(
    http.get(ME, noSession),
    http.get(USERS, () => {
      asked = true
      return notFound()
    }),
  )

  const { container } = render(<DevEntryPage />)

  await vi.waitFor(() => expect(asked).toBe(true))
  await vi.waitFor(() => expect(container.innerHTML).toBe(''))
  expect(screen.queryByText('Entrada de desarrollo')).toBeNull()
})

test.each([
  ['the API cannot be reached', apiDown, 'No se puede llegar a la API.'],
  ['the API answers with an error', internalError, 'La API respondió con un error.'],
  ['the API does not answer in time', neverAnswers, 'La API no respondió a tiempo.'],
])('case 62: when %s, it is an error with a retry', async (_, answer, message) => {
  api.use(http.get(ME, answer))

  render(<DevEntryPage timeoutMs={50} />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('No se pudo consultar la sesión')
  expect(alert.textContent).toContain(message)
  screen.getByRole('button', { name: 'Reintentar' })
})

test('case 62: a list that fails is an error too, not an empty list', async () => {
  api.use(http.get(ME, noSession), http.get(USERS, internalError))

  render(<DevEntryPage />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('La API respondió con un error.')
  expect(screen.queryByText('No hay usuarios de prueba')).toBeNull()
})

test('case 63: retrying after an error asks again and ends with the list', async () => {
  api.use(http.get(ME, noSession), http.get(USERS, usersAre([LUCIA])))
  // The handler added last runs first: the first request fails.
  api.use(http.get(ME, apiDown, { once: true }))

  render(<DevEntryPage />)
  ;(await screen.findByRole('button', { name: 'Reintentar' })).click()

  await screen.findByRole('button', { name: 'Entrar como Lucía' })
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case 64: when entering fails, it is an error and nobody is in', async () => {
  api.use(
    http.get(ME, noSession),
    http.get(USERS, usersAre([LUCIA])),
    http.post(SESSION, internalError),
  )

  render(<DevEntryPage />)
  ;(await screen.findByRole('button', { name: 'Entrar como Lucía' })).click()

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('La API respondió con un error.')
  screen.getByRole('button', { name: 'Reintentar' })
  expect(screen.queryByText('Entraste como Lucía')).toBeNull()
})

test('case 65: pressing a button that goes away moves the focus to the status line', async () => {
  api.use(
    http.get(ME, noSession),
    http.get(USERS, usersAre([LUCIA])),
    http.post(SESSION, async () => {
      await delay('infinite')
      return noContent()
    }),
  )

  render(<DevEntryPage />)
  const enter = await screen.findByRole('button', { name: 'Entrar como Lucía' })
  enter.focus()
  expect(document.activeElement).toBe(enter)
  enter.click()

  await screen.findByText('Consultando la sesión…')
  expect(document.activeElement).toBe(screen.getByRole('status'))
})

test('case 66: closing the screen cancels the request in progress', async () => {
  api.use(http.get(ME, neverAnswers))
  // What the page hands to the browser with its request: the signal that cancels it.
  const sent = vi.spyOn(globalThis, 'fetch')

  const { unmount } = render(<DevEntryPage />)
  await vi.waitFor(() => expect(sent).toHaveBeenCalledTimes(1))
  const signal = sent.mock.calls[0][1]?.signal
  expect(signal?.aborted).toBe(false)
  unmount()

  expect(signal?.aborted).toBe(true)
})

test('case 67: what changes something is sent as JSON, which the API requires', async () => {
  const calls = apiWithTheThreeUsers()

  render(<DevEntryPage />)
  ;(await screen.findByRole('button', { name: 'Entrar como Pablo' })).click()
  ;(await screen.findByRole('button', { name: 'Cerrar sesión' })).click()
  await screen.findByRole('button', { name: 'Entrar como Pablo' })

  expect(calls.map((call) => [call.path, call.contentType])).toEqual([
    ['session', 'application/json'],
    ['logout', 'application/json'],
  ])
})

// Cases 22 to 28 of issue #84: entering the demo environment with a personal link (ADR 0016).

const ANA = { id: crypto.randomUUID(), name: 'Ana' }
const LINK_VALUE = 'the-value-of-the-link'
const NOTICE_REQUIRED = { error: 'test_notice_required', notice_version: 'demo-1' }

function openLink() {
  window.history.replaceState(null, '', `/app/#${LINK_VALUE}`)
}

function closeLink() {
  window.history.replaceState(null, '', '/')
}

test('case 22: the link goes in the body and leaves the address bar before the answer', async () => {
  openLink()
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  const bodies: unknown[] = []
  api.use(
    http.post(SESSION, async ({ request }) => {
      bodies.push(await request.json())
      await pending
      return noContent()
    }),
    http.get(ME, sessionOf(ANA)),
  )

  render(<DevEntryPage />)

  await vi.waitFor(() => expect(bodies).toEqual([{ access_token: LINK_VALUE }]))
  expect(window.location.hash).toBe('')
  answer()
  await screen.findByText('Entraste como Ana')
  closeLink()
})

test('case 23: the first time it shows the notice, and only accepting it enters', async () => {
  openLink()
  const bodies: unknown[] = []
  let accepted = false
  api.use(
    http.post(SESSION, async ({ request }) => {
      const body = (await request.json()) as { accept_test_notice?: string }
      bodies.push(body)
      accepted = body.accept_test_notice === 'demo-1'
      return accepted ? noContent() : HttpResponse.json(NOTICE_REQUIRED, { status: 409 })
    }),
    http.get(ME, () => (accepted ? HttpResponse.json(ANA) : noSession())),
  )

  render(<DevEntryPage />)

  const accept = await screen.findByRole('button', { name: 'Acepto' })
  screen.getByText(/entorno de prueba/)
  screen.getByText(/proveedor de IA/)
  screen.getByText(/pueden borrarse sin aviso/)
  expect(screen.queryByText('Entraste como Ana')).toBeNull()
  expect(bodies).toEqual([{ access_token: LINK_VALUE }])

  accept.click()

  await screen.findByText('Entraste como Ana')
  expect(bodies[1]).toEqual({ access_token: LINK_VALUE, accept_test_notice: 'demo-1' })
  closeLink()
})

test('case 24: a link that does not work says so, without offering a retry', async () => {
  openLink()
  api.use(http.post(SESSION, notFound))

  render(<DevEntryPage />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Este enlace ya no sirve')
  expect(screen.queryByRole('button', { name: 'Reintentar' })).toBeNull()
  closeLink()
})

test('case 25: when the network fails, retrying sends the link again', async () => {
  openLink()
  const bodies: unknown[] = []
  let failing = true
  api.use(
    http.post(SESSION, async ({ request }) => {
      bodies.push(await request.json())
      return failing ? HttpResponse.error() : noContent()
    }),
    http.get(ME, sessionOf(ANA)),
  )

  render(<DevEntryPage />)

  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  expect(window.location.hash).toBe('')
  failing = false
  retry.click()

  await screen.findByText('Entraste como Ana')
  expect(bodies).toEqual([{ access_token: LINK_VALUE }, { access_token: LINK_VALUE }])
  closeLink()
})

test('case 26: while the link is being checked, the status line says so', async () => {
  openLink()
  api.use(http.post(SESSION, neverAnswers))

  render(<DevEntryPage />)

  expect(screen.getByRole('status').textContent).toBe('Consultando la sesión…')
  closeLink()
})

test('case 27: with the session of someone else open, the link enters its own account', async () => {
  openLink()
  let entered = false
  api.use(
    http.post(SESSION, () => {
      entered = true
      return noContent()
    }),
    http.get(ME, () => HttpResponse.json(entered ? ANA : PABLO)),
  )

  render(<DevEntryPage />)

  await screen.findByText('Entraste como Ana')
  expect(screen.queryByText('Entraste como Pablo')).toBeNull()
  closeLink()
})

test('case 29: when the notice shows up, the status line announces it', async () => {
  openLink()
  api.use(http.post(SESSION, () => HttpResponse.json(NOTICE_REQUIRED, { status: 409 })))

  render(<DevEntryPage />)

  await screen.findByRole('button', { name: 'Acepto' })
  expect(screen.getByRole('status').textContent).toBe('Antes de entrar, leé este aviso')
  closeLink()
})

test('case 28: without a link or a session in demo, the card is never drawn', async () => {
  closeLink()
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  let asked = false
  api.use(
    http.get(ME, noSession),
    http.get(USERS, async () => {
      asked = true
      await pending
      return notFound()
    }),
  )

  const { container } = render(<DevEntryPage />)

  expect(screen.queryByText('Entrada de desarrollo')).toBeNull()
  await vi.waitFor(() => expect(asked).toBe(true))
  expect(screen.queryByText('Entrada de desarrollo')).toBeNull()
  answer()
  await vi.waitFor(() => expect(container.innerHTML).toBe(''))
})
