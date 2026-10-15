/**
 * Cases C1-31 and C2-11 of FEAT-001 (docs/features/FEAT-001/spec.md): how the accounts screen
 * appears once someone enters, and goes away when the session ends. The whole dashboard is rendered, with the API simulated at the
 * network level.
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest'
import App from './App'

const LUCIA = { id: '4379d06b-46d3-4f2e-a59e-addcb32388f8', name: 'Lucía' }
const ACCOUNTS = [
  { id: 'a1', name: 'Efectivo', type: 'cash', currency: 'ARS', balance: 25000, balance_kind: 'balance' },
]

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

test('case C1-31: choosing Lucía in the entry shows the menu and her accounts first', async () => {
  let signedIn = false
  api.use(
    http.get('*/healthz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/readyz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/me', () =>
      signedIn ? HttpResponse.json(LUCIA) : HttpResponse.json({ error: 'unauthorized' }, { status: 401 }),
    ),
    http.get('*/dev/users', () => HttpResponse.json({ users: [LUCIA] })),
    http.post('*/dev/session', () => {
      signedIn = true
      return new HttpResponse(null, { status: 204 })
    }),
    http.get('*/accounts', () => HttpResponse.json({ accounts: ACCOUNTS })),
  )

  render(<App />)
  expect(screen.queryByRole('heading', { name: 'Tus cuentas' })).toBeNull()
  ;(await screen.findByRole('button', { name: 'Entrar como Lucía' })).click()

  const nav = await screen.findByRole('navigation', { name: 'Menú principal' })
  await screen.findByRole('heading', { name: 'Tus cuentas' })
  await screen.findByText('Efectivo', { selector: '.account__name' })
  expect(within(nav).getByRole('button', { name: 'Cuentas' }).getAttribute('aria-current')).toBe('page')
  expect(screen.queryByRole('heading', { name: 'Entrada de desarrollo' })).toBeNull()
})

test('case C2-11: when the session expired, the entry comes back', async () => {
  // Lucía is in until the accounts are asked for, and from then on the session is over.
  let signedIn = true
  let accountsAskedFor = false
  api.use(
    http.get('*/healthz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/readyz', () => HttpResponse.json({ status: 'ok' })),
    http.get('*/me', () =>
      signedIn ? HttpResponse.json(LUCIA) : HttpResponse.json({ error: 'unauthorized' }, { status: 401 }),
    ),
    http.get('*/dev/users', () => HttpResponse.json({ users: [LUCIA] })),
    http.get('*/accounts', () => {
      accountsAskedFor = true
      signedIn = false
      return HttpResponse.json({ error: 'unauthorized' }, { status: 401 })
    }),
  )

  render(<App />)

  await screen.findByRole('button', { name: 'Entrar como Lucía' })
  expect(accountsAskedFor).toBe(true)
  expect(screen.queryByRole('heading', { name: 'Tus cuentas' })).toBeNull()
  expect(document.querySelectorAll('.account__amount')).toHaveLength(0)
})
