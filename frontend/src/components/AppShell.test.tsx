/**
 * Cases T-01 to T-06 of the task that brings Tailwind and shadcn/ui (ADR 0027): the side
 * menu of the dashboard. The whole dashboard is rendered, with the API simulated at the
 * network level. The cases are in the description of its pull request. Cases 33, 34 and 35
 * are of issue #84.
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest'
import App from '../App'

const LUCIA = { id: crypto.randomUUID(), name: 'Lucía' }
const ACCOUNTS = [
  { id: 'a1', name: 'Efectivo', type: 'cash', currency: 'ARS', balance: 25000, balance_kind: 'balance' },
]
const noSession = () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })

// The web chat is off here: its route answers 404, as the API does when it is turned off.
const chatOff = http.get('*/chat/messages', () => HttpResponse.json({ error: 'not_found' }, { status: 404 }))
const api = setupServer(chatOff)

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
  // What the browser remembers of an earlier test must not reach the next one.
  window.localStorage.clear()
  window.history.replaceState(null, '', '/')
})
afterAll(() => api.close())

/** An API where Lucía is in until she closes her session. */
function apiWithLuciaIn() {
  let signedIn = true
  api.use(
    http.get('*/healthz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/readyz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/me', () => (signedIn ? HttpResponse.json(LUCIA) : noSession())),
    http.get('*/dev/users', () => HttpResponse.json({ users: [LUCIA] })),
    http.get('*/accounts', () => HttpResponse.json({ accounts: ACCOUNTS })),
    http.post('*/auth/logout', () => {
      signedIn = false
      return new HttpResponse(null, { status: 204 })
    }),
  )
}

async function menu(): Promise<HTMLElement> {
  return screen.findByRole('navigation', { name: 'Menú principal' })
}

test('case T-01: without a session there is no menu, only the entry and the status', async () => {
  api.use(
    http.get('*/healthz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/readyz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/me', noSession),
    http.get('*/dev/users', () => HttpResponse.json({ users: [LUCIA] })),
  )

  render(<App />)

  await screen.findByRole('button', { name: 'Entrar como Lucía' })
  screen.getByRole('heading', { name: 'Entrada de desarrollo' })
  screen.getByRole('heading', { name: 'Estado del sistema' })
  expect(screen.queryByRole('navigation')).toBeNull()
})

test('case T-02: with a session, the menu has its sections and the accounts are the current screen', async () => {
  apiWithLuciaIn()

  render(<App />)

  const nav = await menu()
  const accounts = within(nav).getByRole('button', { name: 'Cuentas' })
  within(nav).getByText('Pruebas')
  const status = within(nav).getByRole('button', { name: 'Estado del sistema' })
  expect(accounts.getAttribute('aria-current')).toBe('page')
  expect(status.getAttribute('aria-current')).toBeNull()
  screen.getByText('Lucía')
  screen.getByRole('button', { name: 'Cerrar sesión' })
  await screen.findByText('Efectivo', { selector: '.account__name' })
})

test('case T-03: choosing the status in the menu shows it and marks it as the current screen', async () => {
  apiWithLuciaIn()

  render(<App />)
  const nav = await menu()
  await screen.findByRole('heading', { name: 'Tus cuentas' })
  within(nav).getByRole('button', { name: 'Estado del sistema' }).click()

  await screen.findByRole('heading', { name: 'Estado del sistema' })
  expect(within(nav).getByRole('button', { name: 'Estado del sistema' }).getAttribute('aria-current')).toBe(
    'page',
  )
  expect(within(nav).getByRole('button', { name: 'Cuentas' }).getAttribute('aria-current')).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Tus cuentas' })).toBeNull()
})

test('case C1-38: the menu leads to the budget screen', async () => {
  // Case C1-38 of FEAT-004 (docs/features/FEAT-004/spec.md).
  apiWithLuciaIn()
  const current = { id: crypto.randomUUID(), period_type: 'monthly', status: 'confirmed', primary_currency: 'ARS' }
  api.use(
    http.get('*/budget-periods', () =>
      HttpResponse.json({
        budget_periods: [
          {
            ...current,
            family_group_id: null,
            family_group_name: null,
            period_start: '2026-10-10',
            period_end: '2026-11-09',
            estimated_income: 1450000,
            can_edit: true,
            is_current: true,
            budgets: [],
          },
        ],
      }),
    ),
    http.get('*/budget-periods/:periodId/summary', () =>
      HttpResponse.json({
        budget_period_id: current.id,
        primary_currency: 'ARS',
        estimated_income: 1450000,
        actual_income: 0,
        total_spent: 3500,
        categories: [{ category: 'Café', budget_id: null, limit_amount: null, spent_amount: 3500, used_percentage: null }],
      }),
    ),
  )

  render(<App />)
  const nav = await menu()
  await screen.findByRole('heading', { name: 'Tus cuentas' })
  within(nav).getByRole('button', { name: 'Presupuesto' }).click()

  await screen.findByRole('heading', { name: 'Tu presupuesto' })
  expect(within(nav).getByRole('button', { name: 'Presupuesto' }).getAttribute('aria-current')).toBe('page')
  expect(within(nav).getByRole('button', { name: 'Cuentas' }).getAttribute('aria-current')).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Tus cuentas' })).toBeNull()
})

test('case T-04: closing the session from the menu brings back the entry, without the menu', async () => {
  apiWithLuciaIn()

  render(<App />)
  await menu()
  screen.getByRole('button', { name: 'Cerrar sesión' }).click()

  await screen.findByRole('button', { name: 'Entrar como Lucía' })
  expect(screen.queryByRole('navigation')).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Tus cuentas' })).toBeNull()
})

test('case T-05: the menu is announced as navigation and every option is a button the keyboard reaches', async () => {
  apiWithLuciaIn()

  render(<App />)
  const nav = await menu()

  // A native button is reached with Tab and pressed with Enter; none takes itself out of the order.
  const options = within(nav).getAllByRole('button')
  expect(options.map((option) => option.textContent)).toEqual(['Cuentas', 'Presupuesto', 'Estado del sistema'])
  expect(options.every((option) => option.tagName === 'BUTTON' && option.tabIndex === 0)).toBe(true)
})

test('case T-06: when closing the session fails, the menu stays and it says why', async () => {
  apiWithLuciaIn()
  api.use(http.post('*/auth/logout', () => HttpResponse.json({ error: 'internal_error' }, { status: 500 })))

  render(<App />)
  await menu()
  screen.getByRole('button', { name: 'Cerrar sesión' }).click()

  const alert = await screen.findByRole('alert')
  within(alert).getByText('No se pudo cerrar la sesión')
  within(alert).getByText('La API respondió con un error.')
  screen.getByRole('navigation', { name: 'Menú principal' })
  expect(screen.queryByRole('button', { name: 'Entrar como Lucía' })).toBeNull()
})

test('case 33: closing every session brings back the entry, without the menu', async () => {
  apiWithLuciaIn()
  let closed = false
  api.use(
    http.get('*/me', () => (closed ? noSession() : HttpResponse.json(LUCIA))),
    http.post('*/auth/logout-all', () => {
      closed = true
      return new HttpResponse(null, { status: 204 })
    }),
  )

  render(<App />)
  await menu()
  ;(await screen.findByRole('button', { name: 'Cerrar todas las sesiones' })).click()

  await screen.findByRole('button', { name: 'Entrar como Lucía' })
  expect(closed).toBe(true)
  expect(screen.queryByRole('navigation')).toBeNull()
})

test('case 33: when closing every session fails, the menu stays and it says why', async () => {
  apiWithLuciaIn()
  api.use(http.post('*/auth/logout-all', () => HttpResponse.json({ error: 'internal_error' }, { status: 500 })))

  render(<App />)
  await menu()
  ;(await screen.findByRole('button', { name: 'Cerrar todas las sesiones' })).click()

  const alert = await screen.findByRole('alert')
  within(alert).getByText('No se pudo cerrar la sesión')
  within(alert).getByText('La API respondió con un error.')
  screen.getByRole('navigation', { name: 'Menú principal' })
  expect(screen.queryByRole('button', { name: 'Entrar como Lucía' })).toBeNull()
})

const ANA = { id: crypto.randomUUID(), name: 'Ana' }
const OPEN_THE_LINK_AGAIN = 'Para volver a entrar, abrí de nuevo tu enlace personal.'

/** An API in demo: Ana enters with her link, and the entry without one does not exist. */
function demoApiWithAnaIn() {
  window.history.replaceState(null, '', '/app/#the-value-of-the-link')
  const session = { alive: false }
  api.use(
    http.get('*/healthz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/readyz', () => HttpResponse.json({ status: 'ok' })),
    http.post('*/dev/session', () => {
      session.alive = true
      return new HttpResponse(null, { status: 204 })
    }),
    http.get('*/me', () => (session.alive ? HttpResponse.json(ANA) : noSession())),
    http.get('*/dev/users', () => HttpResponse.json({ error: 'not_found' }, { status: 404 })),
    http.get('*/accounts', () => (session.alive ? HttpResponse.json({ accounts: ACCOUNTS }) : noSession())),
    // Only asked for in case 34, once the session already ended.
    http.get('*/budget-periods', noSession),
    http.post('*/auth/logout', () => {
      session.alive = false
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return session
}

test('case 34: when the session ends while in use, it says to open the link again', async () => {
  const session = demoApiWithAnaIn()
  render(<App />)
  const nav = await menu()
  await screen.findByText('Efectivo', { selector: '.account__name' })

  // Thirty minutes later the session expired, and the next screen asks the API.
  session.alive = false
  within(nav).getByRole('button', { name: 'Presupuesto' }).click()

  await screen.findByText(OPEN_THE_LINK_AGAIN)
  expect(screen.queryByRole('navigation')).toBeNull()
})

test('case 35: closing the session after entering with a link says to open the link again', async () => {
  demoApiWithAnaIn()
  render(<App />)
  await menu()

  screen.getByRole('button', { name: 'Cerrar sesión' }).click()

  await screen.findByText(OPEN_THE_LINK_AGAIN)
  expect(screen.queryByRole('navigation')).toBeNull()
})
