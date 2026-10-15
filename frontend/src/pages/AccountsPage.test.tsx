/**
 * Cases C1-25 to C1-30 and C2-07 to C2-10 of FEAT-001 (docs/features/FEAT-001/spec.md): the
 * four states of the accounts screen. The API is simulated at the network level,
 * so the page and its API call are tested together.
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest'
import { AccountsPage } from './AccountsPage'

const ACCOUNTS = '*/accounts'

type Account = {
  id: string
  name: string
  type: string
  currency: string
  balance: number
  balance_kind: string
}

const account = (
  id: string,
  name: string,
  type: string,
  currency: string,
  balance: number,
  balance_kind = 'balance',
): Account => ({ id, name, type, currency, balance, balance_kind })

const CASH = account('a1', 'Efectivo', 'cash', 'ARS', 25000)
const GALICIA = account('a2', 'Galicia pesos', 'bank_account', 'ARS', 350000)
const MERCADO_PAGO = account('a3', 'Mercado Pago', 'digital_wallet', 'ARS', 80000)
const GALICIA_USD = account('a4', 'Galicia USD', 'bank_account', 'USD', 500)
const LUCIA = [CASH, GALICIA, MERCADO_PAGO, GALICIA_USD]

const accountsAre = (accounts: Account[]) => () => HttpResponse.json({ accounts })
const nothing = () => {}

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

/** The text of an element with every kind of space as a plain one, as it is read. */
const read = (element: Element) => (element.textContent ?? '').replace(/\s/g, ' ')

/** The rows of a group, each as "name · type · amount". */
function rowsOf(group: HTMLElement): string[] {
  return within(group)
    .getAllByRole('listitem')
    .map((row) => Array.from(row.children).map(read).join(' · '))
}

function group(name: string): HTMLElement {
  return screen.getByRole('region', { name })
}

test('case C1-25: while the accounts are being asked for, it says so and shows no balance', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(ACCOUNTS, async () => {
      await pending
      return accountsAre(LUCIA)()
    }),
  )

  render(<AccountsPage onNoSession={nothing} />)

  expect(screen.getByRole('status').textContent).toBe('Consultando tus cuentas…')
  expect(screen.queryAllByRole('listitem')).toHaveLength(0)
  answer()
  await screen.findByRole('region', { name: 'Cuentas en ARS' })
})

test('case C1-26: the accounts of Lucía, grouped by currency, in order, with no total', async () => {
  api.use(http.get(ACCOUNTS, accountsAre(LUCIA)))

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByRole('region', { name: 'Cuentas en ARS' })
  const headings = screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
  expect(headings).toEqual(['Cuentas en ARS', 'Cuentas en USD'])
  expect(rowsOf(group('Cuentas en ARS'))).toEqual([
    'Efectivo · Efectivo · $ 25.000,00',
    'Galicia pesos · Banco · $ 350.000,00',
    'Mercado Pago · Billetera · $ 80.000,00',
  ])
  expect(rowsOf(group('Cuentas en USD'))).toEqual(['Galicia USD · Banco · US$ 500,00'])
  // Four accounts, four amounts: nothing added up anywhere.
  expect(document.querySelectorAll('.account__amount')).toHaveLength(4)
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case C1-27: an investment account goes apart, with the net contributed', async () => {
  const balanz = account('a5', 'Balanz USD', 'broker', 'USD', 3100, 'net_contributed')
  api.use(http.get(ACCOUNTS, accountsAre([...LUCIA, balanz])))

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByRole('region', { name: 'Inversiones' })
  expect(rowsOf(group('Inversiones'))).toEqual(['Balanz USD · Aportado neto · US$ 3.100,00'])
  expect(rowsOf(group('Cuentas en USD'))).toEqual(['Galicia USD · Banco · US$ 500,00'])
})

test('case C1-28: an account others owe does not appear', async () => {
  const owed = account('a6', 'Me debe Juan', 'receivable', 'ARS', 30000)
  api.use(http.get(ACCOUNTS, accountsAre([...LUCIA, owed])))

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByRole('region', { name: 'Cuentas en ARS' })
  expect(screen.queryByText('Me debe Juan')).toBeNull()
  expect(screen.getAllByRole('listitem')).toHaveLength(4)
})

test('case C1-29: a negative balance is shown with its sign', async () => {
  const visa = account('a7', 'Visa', 'credit_card', 'ARS', -50000)
  api.use(http.get(ACCOUNTS, accountsAre([visa])))

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByRole('region', { name: 'Cuentas en ARS' })
  expect(rowsOf(group('Cuentas en ARS'))).toEqual(['Visa · Tarjeta de crédito · -$ 50.000,00'])
  expect(document.querySelector('.account__amount')?.classList).toContain(
    'account__amount--negative',
  )
})

test('case C1-30: a balance is shown as it arrives, without sums of its own', async () => {
  // The body is written by hand, so that the amount travels exactly as the API writes it.
  api.use(
    http.get(
      ACCOUNTS,
      () =>
        new HttpResponse(
          '{"accounts":[{"id":"a8","name":"Caja chica","type":"cash","currency":"ARS",' +
            '"balance":0.30,"balance_kind":"balance"}]}',
          { headers: { 'Content-Type': 'application/json' } },
        ),
    ),
  )

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByRole('region', { name: 'Cuentas en ARS' })
  expect(rowsOf(group('Cuentas en ARS'))).toEqual(['Caja chica · Efectivo · $ 0,30'])
})

test('case C2-07: without accounts it is empty, not an error', async () => {
  api.use(http.get(ACCOUNTS, accountsAre([])))

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByText('Todavía no tenés cuentas')
  screen.getByText('Las cuentas se dan de alta conversando con Platita.')
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Reintentar' })).toBeNull()
})

test('case C2-08: with only accounts others owe, it is empty too', async () => {
  const owed = account('a6', 'Me debe Juan', 'receivable', 'ARS', 30000)
  api.use(http.get(ACCOUNTS, accountsAre([owed])))

  render(<AccountsPage onNoSession={nothing} />)

  await screen.findByText('Todavía no tenés cuentas')
  expect(screen.queryByText('Me debe Juan')).toBeNull()
  expect(screen.queryByRole('alert')).toBeNull()
})

test.each([
  ['the API answers 500', () => HttpResponse.json({ error: 'internal_error' }, { status: 500 }), 'La API respondió con un error.'],
  ['the API cannot be reached', () => HttpResponse.error(), 'No se puede llegar a la API.'],
  [
    'the API does not answer in time',
    async () => {
      await delay('infinite')
      return accountsAre(LUCIA)()
    },
    'La API no respondió a tiempo.',
  ],
])('case C2-09: an error for each cause, with no balance: %s', async (_, answer, cause) => {
  api.use(http.get(ACCOUNTS, answer))

  render(<AccountsPage onNoSession={nothing} timeoutMs={50} />)

  const alert = await screen.findByRole('alert')
  within(alert).getByText('No se pudieron consultar tus cuentas')
  within(alert).getByText(cause)
  within(alert).getByRole('button', { name: 'Reintentar' })
  expect(screen.queryAllByRole('listitem')).toHaveLength(0)
})

test('case C2-10: retrying after an error brings the accounts', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(ACCOUNTS, () => HttpResponse.json({ error: 'internal_error' }, { status: 500 }), {
      once: true,
    }),
  )

  render(<AccountsPage onNoSession={nothing} />)
  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  api.use(
    http.get(ACCOUNTS, async () => {
      await pending
      return accountsAre(LUCIA)()
    }),
  )
  retry.click()

  const status = await screen.findByText('Consultando tus cuentas…')
  expect(document.activeElement).toBe(status)
  answer()
  await screen.findByRole('region', { name: 'Cuentas en ARS' })
  expect(screen.queryByRole('alert')).toBeNull()
})
