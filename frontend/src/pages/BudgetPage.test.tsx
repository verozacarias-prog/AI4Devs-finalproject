/**
 * Cases C1-26 to C1-37, C2-09 to C2-14 and C3-02 to C3-05 of FEAT-004 (docs/features/FEAT-004/spec.md), and
 * C1-23, C2-30 and C2-31 of FEAT-005 (docs/features/FEAT-005/spec.md): the four states of the budget screen. The API is simulated at the network level, so the page and its API calls are
 * tested together.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest'
import { BudgetPage } from './BudgetPage'

const PERIODS = '*/budget-periods'
const SUMMARY = '*/budget-periods/:periodId/summary'
const DETAIL = '*/budgets/:budgetId'

type Period = {
  id: string
  family_group_id: string | null
  family_group_name: string | null
  period_type: string
  period_start: string
  period_end: string
  status: string
  primary_currency: string
  estimated_income: number
  can_edit: boolean
  is_current: boolean
  budgets: { id: string; category_id: string; category: string; limit_amount: number }[]
}

type Category = {
  category: string
  budget_id: string | null
  limit_amount: number | null
  spent_amount: number
  used_percentage: number | null
}

type Movement = {
  id: string
  transaction_date: string
  description: string | null
  type: string
  amount: number
  currency: string
  budget_amount: number
  exchange_rate: number | null
  account: string
  source: string
}

const SUPERMERCADO = crypto.randomUUID()
const TRANSPORTE = crypto.randomUUID()

function period(start: string, end: string, overrides: Partial<Period> = {}): Period {
  return {
    id: crypto.randomUUID(),
    family_group_id: null,
    family_group_name: null,
    period_type: 'monthly',
    period_start: start,
    period_end: end,
    status: 'confirmed',
    primary_currency: 'ARS',
    estimated_income: 1450000,
    can_edit: true,
    is_current: false,
    budgets: [],
    ...overrides,
  }
}

const CURRENT = period('2026-10-10', '2026-11-09', { is_current: true })
const PREVIOUS = period('2026-09-10', '2026-10-09')

const limited = (category: string, budgetId: string, limit: number, spent: number, percentage: number): Category => ({
  category,
  budget_id: budgetId,
  limit_amount: limit,
  spent_amount: spent,
  used_percentage: percentage,
})

const unlimited = (category: string, spent: number): Category => ({
  category,
  budget_id: null,
  limit_amount: null,
  spent_amount: spent,
  used_percentage: null,
})

const LUCIA_CATEGORIES = [
  unlimited('Café', 3500),
  limited('Supermercado', SUPERMERCADO, 300000, 24716.04, 8.2),
  limited('Transporte', TRANSPORTE, 80000, 80040, 100.1),
]

function summary(periodId: string, categories: Category[], totalSpent: number, actualIncome = 1500000) {
  return {
    budget_period_id: periodId,
    primary_currency: 'ARS',
    estimated_income: 1450000,
    actual_income: actualIncome,
    total_spent: totalSpent,
    categories,
  }
}

function movement(date: string, type: string, amount: number, currency: string, overrides: Partial<Movement> = {}): Movement {
  return {
    id: crypto.randomUUID(),
    transaction_date: date,
    description: null,
    type,
    amount,
    currency,
    budget_amount: amount,
    exchange_rate: null,
    account: 'Galicia pesos',
    source: 'manual',
    ...overrides,
  }
}

function detail(budgetId: string, spent: number, percentage: number, movements: Movement[]) {
  return {
    id: budgetId,
    budget_period_id: CURRENT.id,
    category: 'Supermercado',
    primary_currency: 'ARS',
    limit_amount: 300000,
    spent_amount: spent,
    used_percentage: percentage,
    transactions: movements,
  }
}

const nothing = () => {}

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

/** What the API was asked for, in order: which period's summary and which budget's detail. */
type Asked = { summaries: string[]; details: string[] }

/** An API with these periods, a summary for each period id, and the given details. */
function apiWith(
  periods: Period[],
  summaries: Record<string, object>,
  details: Record<string, object> = {},
): Asked {
  const asked: Asked = { summaries: [], details: [] }
  api.use(
    http.get(PERIODS, () => HttpResponse.json({ budget_periods: periods })),
    http.get(SUMMARY, ({ params }) => {
      const id = String(params.periodId)
      asked.summaries.push(id)
      return HttpResponse.json(summaries[id])
    }),
    http.get(DETAIL, ({ params }) => {
      const id = String(params.budgetId)
      asked.details.push(id)
      return HttpResponse.json(details[id])
    }),
  )
  return asked
}

/** The text of an element with every kind of space as a plain one, as it is read. */
const read = (element: Element | null) => (element?.textContent ?? '').replace(/\s/g, ' ')

const selector = () => screen.getByRole('combobox', { name: 'Período' }) as HTMLSelectElement

const chosenPeriod = () => read(selector().selectedOptions[0])

/** The text after a label of the summary, such as "Ingreso estimado". */
const figure = (label: string) => read(screen.getByText(label).nextElementSibling)

/** The row of a category in the summary, by its name. */
function categoryRow(name: string): HTMLElement {
  const row = screen.getByText(name, { selector: '.budget-category__name' }).closest('.budget-category')
  if (!(row instanceof HTMLElement)) throw new Error(`no row for ${name}`)
  return row
}

const part = (row: Element, name: string) => row.querySelector(`.budget-category__${name}`)

const fill = (row: Element) => row.querySelector<HTMLElement>('.budget-bar__fill')

/** The rows of the detail, each as its parts in order, joined with " · ". */
function movementRows(): string[] {
  return Array.from(document.querySelectorAll('.budget-movement')).map((row) =>
    Array.from(row.children)
      .map(read)
      .filter((text) => text !== '')
      .join(' · '),
  )
}

test('case C1-26: while the budget is being asked for, it says so and shows no amount', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(PERIODS, async () => {
      await pending
      return HttpResponse.json({ budget_periods: [CURRENT] })
    }),
    http.get(SUMMARY, () => HttpResponse.json(summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04))),
  )

  render(<BudgetPage onNoSession={nothing} />)

  expect(screen.getByRole('status').textContent).toBe('Consultando tu presupuesto…')
  expect(document.querySelectorAll('.budget-category')).toHaveLength(0)
  expect(document.querySelectorAll('.budget-bar')).toHaveLength(0)
  expect(document.body.textContent).not.toContain('$')
  answer()
  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
})

test('case C1-27: it opens the period that covers today', async () => {
  const asked = apiWith([CURRENT, PREVIOUS], {
    [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04),
    [PREVIOUS.id]: summary(PREVIOUS.id, [], 0),
  })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  expect(chosenPeriod()).toBe('Personal · del 10/10/2026 al 9/11/2026')
  expect(asked.summaries).toEqual([CURRENT.id])
})

test('case C1-28: a draft period warns that it still has to be confirmed', async () => {
  const draft = { ...CURRENT, status: 'draft' }
  apiWith([draft, PREVIOUS], {
    [draft.id]: summary(
      draft.id,
      [limited('Supermercado', SUPERMERCADO, 300000, 0, 0), limited('Transporte', TRANSPORTE, 80000, 0, 0)],
      0,
      0,
    ),
  })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  screen.getByText('Este período está en borrador: confirmalo para que reciba movimientos')
  expect(read(part(categoryRow('Supermercado'), 'spent'))).toBe('$ 0,00 de $ 300.000,00')
  expect(read(part(categoryRow('Transporte'), 'spent'))).toBe('$ 0,00 de $ 80.000,00')
})

test('case C1-29: the summary of the period of Lucía', async () => {
  apiWith([CURRENT, PREVIOUS], { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04) })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  expect(figure('Ingreso estimado')).toBe('$ 1.450.000,00')
  expect(figure('Ingreso real')).toBe('$ 1.500.000,00')
  expect(figure('Total gastado')).toBe('$ 108.256,04')
  const names = Array.from(document.querySelectorAll('.budget-category__name')).map(read)
  expect(names).toEqual(['Café', 'Supermercado', 'Transporte'])

  const cafe = categoryRow('Café')
  expect(read(part(cafe, 'spent'))).toBe('$ 3.500,00')
  expect(read(part(cafe, 'no-limit'))).toBe('Sin tope')
  expect(part(cafe, 'no-limit')?.classList).toContain('text-muted-foreground')
  expect(part(cafe, 'percentage')).toBeNull()
  expect(cafe.querySelector('.budget-bar')).toBeNull()

  const supermercado = categoryRow('Supermercado')
  expect(read(part(supermercado, 'spent'))).toBe('$ 24.716,04 de $ 300.000,00')
  expect(read(part(supermercado, 'percentage'))).toBe('8,2 %')
  expect(supermercado.querySelector('.budget-bar')).not.toBeNull()

  const transporte = categoryRow('Transporte')
  expect(read(part(transporte, 'spent'))).toBe('$ 80.040,00 de $ 80.000,00')
  expect(read(part(transporte, 'percentage'))).toBe('100,1 %')
  expect(transporte.querySelector('.budget-bar')).not.toBeNull()
})

test('case C1-30: the bar says whether the category is near its limit or over it', async () => {
  const ids = [crypto.randomUUID(), crypto.randomUUID(), crypto.randomUUID(), crypto.randomUUID()]
  apiWith([CURRENT], {
    [CURRENT.id]: summary(
      CURRENT.id,
      [
        limited('A', ids[0], 1000, 800, 80.0),
        limited('B', ids[1], 1000, 801, 80.1),
        limited('C', ids[2], 1000, 1000, 100.0),
        limited('D', ids[3], 1000, 1001, 100.1),
      ],
      3602,
    ),
  })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('A', { selector: '.budget-category__name' })
  const bar = (name: string) => categoryRow(name).querySelector('.budget-bar')

  expect(bar('A')?.classList).toContain('budget-bar--normal')
  expect(categoryRow('A').textContent).not.toMatch(/Cerca del tope|Excedido/)

  for (const name of ['B', 'C']) {
    expect(bar(name)?.classList).toContain('budget-bar--near')
    expect(fill(categoryRow(name))?.classList).toContain('bg-warning')
    within(categoryRow(name)).getByText('Cerca del tope')
  }

  expect(bar('D')?.classList).toContain('budget-bar--over')
  expect(fill(categoryRow('D'))?.classList).toContain('bg-destructive')
  expect(fill(categoryRow('D'))?.style.width).toBe('100%')
  within(categoryRow('D')).getByText('Excedido')
})

test('case C1-31: the amounts are shown as they arrive, without sums of its own', async () => {
  // The body is written by hand, so that the total travels exactly as the API writes it.
  api.use(
    http.get(PERIODS, () => HttpResponse.json({ budget_periods: [CURRENT] })),
    http.get(
      SUMMARY,
      () =>
        new HttpResponse(
          `{"budget_period_id":"${CURRENT.id}","primary_currency":"ARS","estimated_income":1450000.00,` +
            '"actual_income":0.00,"total_spent":0.30,"categories":[{"category":"Supermercado",' +
            `"budget_id":"${SUPERMERCADO}","limit_amount":300000.00,"spent_amount":0.10,"used_percentage":0.0}]}`,
          { headers: { 'Content-Type': 'application/json' } },
        ),
    ),
  )

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  expect(figure('Total gastado')).toBe('$ 0,30')
})

test('case C1-32: a negative spent is shown with its sign', async () => {
  apiWith([CURRENT], {
    [CURRENT.id]: summary(CURRENT.id, [limited('Supermercado', SUPERMERCADO, 300000, -5000, -1.7)], -5000),
  })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  const row = categoryRow('Supermercado')
  expect(read(part(row, 'spent'))).toBe('-$ 5.000,00 de $ 300.000,00')
  expect(read(part(row, 'percentage'))).toBe('-1,7 %')
  expect(fill(row)?.style.width).toBe('0%')
})

test('case C1-33: another period is chosen, and the one of a group says its name', async () => {
  const next = period('2026-11-10', '2026-12-09', { status: 'draft' })
  const home = period('2026-10-10', '2026-11-09', {
    family_group_id: crypto.randomUUID(),
    family_group_name: 'Casa',
    can_edit: false,
    is_current: true,
  })
  const asked = apiWith([next, CURRENT, home, PREVIOUS], {
    [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04),
    [PREVIOUS.id]: summary(PREVIOUS.id, [limited('Supermercado', SUPERMERCADO, 280000, 154500, 55.2)], 154500),
  })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Transporte', { selector: '.budget-category__name' })
  expect(within(selector()).getAllByRole('option').map(read)).toEqual([
    'Personal · del 10/11/2026 al 9/12/2026 · Borrador',
    'Personal · del 10/10/2026 al 9/11/2026',
    'Casa · del 10/10/2026 al 9/11/2026',
    'Personal · del 10/9/2026 al 9/10/2026',
  ])

  fireEvent.change(selector(), { target: { value: PREVIOUS.id } })

  await screen.findByText('$ 154.500,00 de $ 280.000,00')
  expect(asked.summaries).toEqual([CURRENT.id, PREVIOUS.id])
  expect(chosenPeriod()).toBe('Personal · del 10/9/2026 al 9/10/2026')
  expect(screen.queryByText('Transporte', { selector: '.budget-category__name' })).toBeNull()
})

const SUPERMERCADO_DETAIL = detail(SUPERMERCADO, 184500, 61.5, [
  movement('2026-10-20', 'income', 30000, 'ARS', { description: 'devolución' }),
  movement('2026-10-18', 'expense', 60000, 'ARS', { description: 'super', source: 'automatic' }),
  movement('2026-10-12', 'expense', 154500, 'ARS'),
])

test('case C1-34: the detail of Supermercado, with its movements', async () => {
  const asked = apiWith(
    [CURRENT, PREVIOUS],
    { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04) },
    { [SUPERMERCADO]: SUPERMERCADO_DETAIL },
  )

  render(<BudgetPage onNoSession={nothing} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Supermercado' }))

  const region = await screen.findByRole('region', { name: 'Supermercado' })
  expect(asked.details).toEqual([SUPERMERCADO])
  expect(read(region.querySelector('.budget-category__spent'))).toBe('$ 184.500,00 de $ 300.000,00')
  expect(read(region.querySelector('.budget-category__percentage'))).toBe('61,5 %')
  expect(movementRows()).toEqual([
    '20/10/2026 · devolución · Reintegro · $ 30.000,00 · Galicia pesos · Manual',
    '18/10/2026 · super · Gasto · $ 60.000,00 · Galicia pesos · Automático',
    '12/10/2026 · Gasto · $ 154.500,00 · Galicia pesos · Manual',
  ])
})

test('case C1-35: an expense in dollars shows its exchange rate', async () => {
  apiWith(
    [CURRENT],
    { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04) },
    {
      [SUPERMERCADO]: detail(SUPERMERCADO, 17345.68, 5.8, [
        movement('2026-10-18', 'expense', 10, 'USD', {
          budget_amount: 12345.68,
          exchange_rate: 1234.5678,
          account: 'Galicia USD',
        }),
        movement('2026-10-12', 'expense', 5000, 'ARS'),
      ]),
    },
  )

  render(<BudgetPage onNoSession={nothing} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Supermercado' }))

  await screen.findByRole('region', { name: 'Supermercado' })
  const [dollars, pesos] = Array.from(document.querySelectorAll('.budget-movement'))
  expect(read(dollars.querySelector('.budget-movement__amount'))).toBe('US$ 10,00')
  expect(read(dollars.querySelector('.budget-movement__exchange-rate'))).toBe('cotización 1.234,5678')
  expect(read(dollars.querySelector('.budget-movement__weight'))).toBe('$ 12.345,68')
  expect(read(pesos.querySelector('.budget-movement__amount'))).toBe('$ 5.000,00')
  expect(pesos.querySelector('.budget-movement__exchange-rate')).toBeNull()
})

test('case C1-36: a category without a limit does not open a detail', async () => {
  const asked = apiWith([CURRENT], { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04) })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByRole('button', { name: 'Supermercado' })
  screen.getByRole('button', { name: 'Transporte' })
  expect(screen.queryByRole('button', { name: 'Café' })).toBeNull()
  expect(screen.queryByRole('link', { name: 'Café' })).toBeNull()
  fireEvent.click(screen.getByText('Café', { selector: '.budget-category__name' }))
  expect(asked.details).toEqual([])
})

test('case C1-37: from the detail it goes back to the summary of the same period', async () => {
  apiWith(
    [CURRENT, PREVIOUS],
    { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04) },
    { [SUPERMERCADO]: SUPERMERCADO_DETAIL },
  )

  render(<BudgetPage onNoSession={nothing} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Supermercado' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Volver al resumen' }))

  await screen.findByText('Transporte', { selector: '.budget-category__name' })
  expect(screen.queryByRole('region', { name: 'Supermercado' })).toBeNull()
  expect(chosenPeriod()).toBe('Personal · del 10/10/2026 al 9/11/2026')
})

const failure = () => HttpResponse.json({ error: 'internal_error' }, { status: 500 })
const noSession = () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })

test('case C2-09: without periods it is empty, not a spinner', async () => {
  const asked = apiWith([], {})

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Todavía no tenés un presupuesto')
  screen.getByText('Cuando armes tu primer período, acá vas a ver cuánto llevás gastado.')
  expect(screen.queryByText('Consultando tu presupuesto…')).toBeNull()
  expect(screen.queryByRole('combobox', { name: 'Período' })).toBeNull()
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Reintentar' })).toBeNull()
  expect(asked.summaries).toEqual([])
})

test('case C2-10: a period without limits or movements is empty', async () => {
  const asked = apiWith([CURRENT, PREVIOUS], {
    [CURRENT.id]: { ...summary(CURRENT.id, [], 0, 0), estimated_income: 0 },
    [PREVIOUS.id]: summary(PREVIOUS.id, LUCIA_CATEGORIES, 108256.04),
  })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Este período todavía no tiene topes ni gastos')
  screen.getByText('Contale tus gastos a Platita y aparecen acá.')
  expect(screen.queryByText('Ingreso estimado')).toBeNull()
  expect(screen.queryByRole('alert')).toBeNull()
  fireEvent.change(selector(), { target: { value: PREVIOUS.id } })
  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  expect(asked.summaries).toEqual([CURRENT.id, PREVIOUS.id])
})

test('case C2-10: an estimated income without limits is not hidden', async () => {
  apiWith([CURRENT], { [CURRENT.id]: summary(CURRENT.id, [], 0, 0) })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByText('Este período todavía no tiene topes ni gastos')
  expect(figure('Ingreso estimado')).toBe('$ 1.450.000,00')
  expect(figure('Ingreso real')).toBe('$ 0,00')
  expect(figure('Total gastado')).toBe('$ 0,00')
  expect(screen.queryByRole('alert')).toBeNull()
})

test.each([
  ['the API answers 500', failure, 'La API respondió con un error.'],
  ['the API cannot be reached', () => HttpResponse.error(), 'No se puede llegar a la API.'],
  [
    'the API does not answer in time',
    async () => {
      await delay('infinite')
      return HttpResponse.json({ budget_periods: [CURRENT] })
    },
    'La API no respondió a tiempo.',
  ],
])('case C2-11: when the periods fail, an error for each cause: %s', async (_, answer, cause) => {
  api.use(http.get(PERIODS, answer))

  render(<BudgetPage onNoSession={nothing} timeoutMs={50} />)

  const alert = await screen.findByRole('alert')
  within(alert).getByText('No se pudo consultar tu presupuesto')
  within(alert).getByText(cause)
  within(alert).getByRole('button', { name: 'Reintentar' })
  expect(document.body.textContent).not.toContain('$')
})

test('case C2-12: when the detail fails, retrying repeats that query', async () => {
  let periodsAsked = 0
  let detailsAsked = 0
  api.use(
    http.get(PERIODS, () => {
      periodsAsked += 1
      return HttpResponse.json({ budget_periods: [CURRENT, PREVIOUS] })
    }),
    http.get(SUMMARY, () => HttpResponse.json(summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04))),
    http.get(DETAIL, () => {
      detailsAsked += 1
      return detailsAsked === 1 ? failure() : HttpResponse.json(SUPERMERCADO_DETAIL)
    }),
  )

  render(<BudgetPage onNoSession={nothing} />)
  fireEvent.click(await screen.findByRole('button', { name: 'Supermercado' }))

  const alert = await screen.findByRole('alert')
  within(alert).getByText('No se pudo consultar tu presupuesto')
  expect(document.querySelectorAll('.budget-category')).toHaveLength(0)
  fireEvent.click(within(alert).getByRole('button', { name: 'Reintentar' }))

  await screen.findByRole('region', { name: 'Supermercado' })
  expect(screen.queryByRole('alert')).toBeNull()
  expect(periodsAsked).toBe(1)
  expect(detailsAsked).toBe(2)
})

test('case C2-13: retrying after an error brings the budget', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(PERIODS, failure, { once: true }),
    http.get(SUMMARY, () => HttpResponse.json(summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04))),
  )

  render(<BudgetPage onNoSession={nothing} />)
  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  api.use(
    http.get(PERIODS, async () => {
      await pending
      return HttpResponse.json({ budget_periods: [CURRENT, PREVIOUS] })
    }),
  )
  fireEvent.click(retry)

  const status = await screen.findByText('Consultando tu presupuesto…')
  expect(document.activeElement).toBe(status)
  answer()
  await screen.findByText('Supermercado', { selector: '.budget-category__name' })
  expect(screen.queryByRole('alert')).toBeNull()
})

test.each([
  ['the periods', () => api.use(http.get(PERIODS, noSession))],
  [
    'the summary',
    () =>
      api.use(
        http.get(PERIODS, () => HttpResponse.json({ budget_periods: [CURRENT] })),
        http.get(SUMMARY, noSession),
      ),
  ],
])('case C2-14: without a session the screen goes back to the entry: %s', async (_, answers) => {
  answers()
  let ended = 0

  render(<BudgetPage onNoSession={() => (ended += 1)} />)

  await waitFor(() => expect(ended).toBe(1))
  expect(screen.queryByRole('alert')).toBeNull()
})

/** Native, enabled and with no tabindex that takes it out of the order: Tab reaches it. */
function expectReachable(control: HTMLElement, tagName: string) {
  expect(control.tagName).toBe(tagName)
  expect((control as HTMLButtonElement | HTMLSelectElement).disabled).toBe(false)
  expect(control.tabIndex).toBe(0)
}

test('case C3-02: the controls have a name and are used with the keyboard', async () => {
  let detailsAsked = 0
  api.use(
    http.get(PERIODS, () => HttpResponse.json({ budget_periods: [CURRENT, PREVIOUS] })),
    http.get(SUMMARY, () => HttpResponse.json(summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04))),
    http.get(DETAIL, () => {
      detailsAsked += 1
      return detailsAsked === 1 ? failure() : HttpResponse.json(SUPERMERCADO_DETAIL)
    }),
  )

  render(<BudgetPage onNoSession={nothing} />)
  const supermercado = await screen.findByRole('button', { name: 'Supermercado' })
  expectReachable(selector(), 'SELECT')
  expectReachable(supermercado, 'BUTTON')
  fireEvent.click(supermercado)
  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  expectReachable(retry, 'BUTTON')
  fireEvent.click(retry)

  expectReachable(await screen.findByRole('button', { name: 'Volver al resumen' }), 'BUTTON')
})

test('case C3-03: each bar announces its percentage and state', async () => {
  const salud = crypto.randomUUID()
  apiWith(
    [CURRENT],
    {
      [CURRENT.id]: summary(
        CURRENT.id,
        [
          limited('Supermercado', SUPERMERCADO, 300000, 135000, 45),
          limited('Salud', salud, 50000, 42500, 85),
          limited('Transporte', TRANSPORTE, 80000, 89600, 112),
        ],
        267100,
      ),
    },
    {
      [TRANSPORTE]: {
        ...detail(TRANSPORTE, 89600, 112, [movement('2026-10-12', 'expense', 89600, 'ARS')]),
        category: 'Transporte',
        limit_amount: 80000,
      },
    },
  )

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByRole('button', { name: 'Transporte' })
  const announced = (meter: HTMLElement) => [meter.getAttribute('aria-label'), meter.getAttribute('aria-valuetext')]
  expect(screen.getAllByRole('meter').map(announced)).toEqual([
    ['Supermercado', '45,0 %'],
    ['Salud', '85,0 %, cerca del tope'],
    ['Transporte', '112,0 %, excedido'],
  ])
  fireEvent.click(screen.getByRole('button', { name: 'Transporte' }))
  await screen.findByRole('region', { name: 'Transporte' })
  expect(screen.getAllByRole('meter').map(announced)).toEqual([['Transporte', '112,0 %, excedido']])
})

test('case C3-04: every amount is written with its currency', async () => {
  apiWith(
    [CURRENT],
    { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 108256.04) },
    {
      [SUPERMERCADO]: detail(SUPERMERCADO, 17345.68, 5.8, [
        movement('2026-10-18', 'expense', 10, 'USD', {
          budget_amount: 12345.68,
          exchange_rate: 1234.5678,
          account: 'Galicia USD',
        }),
        movement('2026-10-12', 'expense', 5000, 'ARS'),
      ]),
    },
  )
  const withCurrency = /^(US)?\$ /

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByRole('button', { name: 'Supermercado' })
  const summaryAmounts = [
    ...['Ingreso estimado', 'Ingreso real', 'Total gastado'].map(figure),
    ...Array.from(document.querySelectorAll('.budget-category__spent')).flatMap((spent) =>
      read(spent).split(' de '),
    ),
  ]
  expect(summaryAmounts).toHaveLength(8)
  for (const amount of summaryAmounts) expect(amount).toMatch(withCurrency)
  fireEvent.click(screen.getByRole('button', { name: 'Supermercado' }))
  await screen.findByRole('region', { name: 'Supermercado' })
  const movementAmounts = Array.from(
    document.querySelectorAll('.budget-movement__amount, .budget-movement__weight'),
  ).map(read)
  expect(movementAmounts).toEqual(['US$ 10,00', '$ 12.345,68', '$ 5.000,00'])
  for (const amount of movementAmounts) expect(amount).toMatch(withCurrency)
})

test('case C3-05: without periods the notice is a heading, not a status', async () => {
  apiWith([], {})

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByRole('heading', { name: 'Todavía no tenés un presupuesto' })
  expect(screen.getByRole('status').textContent).toBe('')
})

test('case C1-23 of FEAT-005: the summary offers to build and to edit', async () => {
  apiWith([CURRENT], { [CURRENT.id]: summary(CURRENT.id, LUCIA_CATEGORIES, 104756.04) })
  api.use(
    http.get('*/categories', () => HttpResponse.json({ categories: [] })),
    http.get('*/currencies', () => HttpResponse.json({ currencies: [] })),
  )

  render(<BudgetPage onNoSession={nothing} />)

  fireEvent.click(await screen.findByRole('button', { name: 'Armar un período' }))
  await screen.findByRole('heading', { name: 'Armar un período' })
  fireEvent.click(await screen.findByRole('button', { name: 'Volver al resumen' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Editar' }))
  await screen.findByRole('heading', { name: 'Editar el período' })
})

test('case C2-30 of FEAT-005: sofia does not see edit on the period of casa', async () => {
  const home = period('2026-10-10', '2026-11-09', {
    family_group_id: crypto.randomUUID(),
    family_group_name: 'Casa',
    can_edit: false,
    is_current: true,
  })
  apiWith([home], { [home.id]: summary(home.id, LUCIA_CATEGORIES, 104756.04) })

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByRole('button', { name: 'Armar un período' })
  expect(screen.queryByRole('button', { name: 'Editar' })).toBeNull()
})

test('case C2-31 of FEAT-005: without periods the first one can be built', async () => {
  apiWith([], {})

  render(<BudgetPage onNoSession={nothing} />)

  await screen.findByRole('heading', { name: 'Todavía no tenés un presupuesto' })
  expect(screen.getByRole('button', { name: 'Armar un período' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Editar' })).toBeNull()
})
