/**
 * Case C1-31 of FEAT-001 (docs/features/FEAT-001/spec.md): once someone enters, the accounts
 * are the first thing seen. The whole dashboard is rendered, with the API simulated at the
 * network level.
 */
import { cleanup, render, screen } from '@testing-library/react'
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

test('case C1-31: choosing Lucía in the entry shows her accounts before anything else', async () => {
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

  const accounts = await screen.findByRole('heading', { name: 'Tus cuentas' })
  await screen.findByText('Efectivo', { selector: '.account__name' })
  const status = screen.getByRole('heading', { name: 'Estado del sistema' })
  const entry = screen.getByRole('heading', { name: 'Entrada de desarrollo' })
  expect(accounts.compareDocumentPosition(status) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(accounts.compareDocumentPosition(entry) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})
