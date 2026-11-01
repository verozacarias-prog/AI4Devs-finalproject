/**
 * Cases C1-22, C1-24 to C1-32, C2-32 to C2-38, C2-43, C2-45, C2-46, C2-48 and C2-49 of FEAT-005 (docs/features/FEAT-005/spec.md): the states of the
 * form of a budget period. The API is simulated at the network level, so the page and its API calls are tested
 * together.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'
import { BudgetPage } from './BudgetPage'
import { BudgetPeriodFormPage } from './BudgetPeriodFormPage'

const PERIODS = '*/budget-periods'
const PERIOD = '*/budget-periods/:periodId'
const CONFIRM = '*/budget-periods/:periodId/confirm'
const SUMMARY = '*/budget-periods/:periodId/summary'
const CATEGORIES = '*/categories'
const CURRENCIES = '*/currencies'
const SHORT_TIMEOUT_MS = 200

const SUPERMERCADO = crypto.randomUUID()
const TRANSPORTE = crypto.randomUUID()
const SALUD = crypto.randomUUID()
const CATEGORY_LIST = [
  { id: SALUD, name: 'Salud', is_base: true },
  { id: SUPERMERCADO, name: 'Supermercado', is_base: true },
  { id: TRANSPORTE, name: 'Transporte', is_base: true },
]

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
    estimated_income: 1450000.5,
    can_edit: true,
    is_current: false,
    budgets: [
      { id: crypto.randomUUID(), category_id: SUPERMERCADO, category: 'Supermercado', limit_amount: 300000 },
      { id: crypto.randomUUID(), category_id: TRANSPORTE, category: 'Transporte', limit_amount: 80000 },
    ],
    ...overrides,
  }
}

const OCTOBER = period('2026-10-10', '2026-11-09', { is_current: true })
const NOVEMBER = period('2026-11-10', '2026-12-09', { status: 'draft', estimated_income: 1500000 })

const nothing = () => {}
const api = setupServer(
  http.get(CURRENCIES, () =>
    HttpResponse.json({
      currencies: [
        { code: 'ARS', name: 'Peso argentino' },
        { code: 'USD', name: 'Dólar estadounidense' },
      ],
    }),
  ),
)

beforeAll(() => api.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

function apiWith(periods: Period[], categories = CATEGORY_LIST) {
  api.use(
    http.get(PERIODS, () => HttpResponse.json({ budget_periods: periods })),
    http.get(CATEGORIES, () => HttpResponse.json({ categories })),
  )
}

/** Answers POST /budget-periods with that period, and keeps the bodies it received. */
function saving(answer: Period) {
  const bodies: Record<string, unknown>[] = []
  api.use(
    http.post(PERIODS, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>)
      return HttpResponse.json(answer, { status: 201 })
    }),
  )
  return bodies
}

function renderForm(periodId: string | null = null, onNoSession = nothing, timeoutMs?: number) {
  render(<BudgetPeriodFormPage periodId={periodId} onDone={nothing} onNoSession={onNoSession} timeoutMs={timeoutMs} />)
}

const field = (label: string) => screen.getByLabelText(label) as HTMLInputElement
const type = (label: string, value: string) => fireEvent.change(field(label), { target: { value } })
const save = () => fireEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))
const ready = () => screen.findByLabelText('Inicio')
const limitRows = () => within(screen.getByRole('table')).getAllByRole('row').slice(1)
const offered = () =>
  within(field('Categoría del tope nuevo'))
    .getAllByRole('option')
    .map((option) => option.textContent)
const addLimit = () => fireEvent.click(screen.getByRole('button', { name: 'Sumar un tope' }))

test('case C1-22: while it prepares the form it says so and shows no fields', async () => {
  api.use(
    http.get(PERIODS, async () => {
      await delay('infinite')
      return HttpResponse.json({})
    }),
    http.get(CATEGORIES, async () => {
      await delay('infinite')
      return HttpResponse.json({})
    }),
  )

  renderForm()

  expect(screen.getByRole('status').textContent).toBe('Preparando el formulario…')
  expect(screen.queryByLabelText('Inicio')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Guardar borrador' })).toBeNull()
})

test('case C1-24: a new period comes as a copy of the last one', async () => {
  apiWith([OCTOBER])

  renderForm()

  await ready()
  expect(field('Cadencia').value).toBe('monthly')
  expect(field('Moneda').value).toBe('ARS')
  expect(field('Ingreso estimado').value).toBe('1450000.5')
  expect(field('Inicio').value).toBe('2026-11-10')
  expect(field('Fin').value).toBe('')
  expect(within(limitRows()[0]).getByRole('rowheader').textContent).toBe('Supermercado')
  expect(field('Monto del tope 1').value).toBe('300000')
  expect(within(limitRows()[1]).getByRole('rowheader').textContent).toBe('Transporte')
  expect(field('Monto del tope 2').value).toBe('80000')
})

test('case C1-25: the last one is the individual one that starts latest even a draft', async () => {
  const group = period('2027-01-10', '2027-02-09', { family_group_id: crypto.randomUUID(), estimated_income: 9 })
  apiWith([group, NOVEMBER, OCTOBER])

  renderForm()

  await ready()
  expect(field('Inicio').value).toBe('2026-12-10')
  expect(field('Ingreso estimado').value).toBe('1500000')
})

test('case C1-26: without a previous period the form comes empty', async () => {
  apiWith([])

  renderForm()

  await ready()
  expect(field('Cadencia').value).toBe('monthly')
  for (const label of ['Moneda', 'Inicio', 'Fin', 'Ingreso estimado']) expect(field(label).value).toBe('')
  expect(screen.queryByRole('table')).toBeNull()
  expect(offered()).toEqual(['Salud', 'Supermercado', 'Transporte'])
})

test('case C1-27: a limit is added and removed among the expense categories', async () => {
  apiWith([OCTOBER])
  const bodies = saving(NOVEMBER)

  renderForm()

  await ready()
  type('Categoría del tope nuevo', SALUD)
  type('Monto del tope nuevo', '40000')
  addLimit()
  fireEvent.click(screen.getByRole('button', { name: 'Quitar el tope 2' }))
  save()

  await screen.findByText('El período quedó guardado.')
  expect(bodies[0].budgets).toEqual([
    { category_id: SUPERMERCADO, limit_amount: '300000' },
    { category_id: SALUD, limit_amount: '40000' },
  ])
})

test('case C1-28: saving sends the amounts as text with their cents', async () => {
  apiWith([OCTOBER])
  const bodies = saving(NOVEMBER)

  renderForm()

  await ready()
  type('Ingreso estimado', '1450000,55')
  type('Monto del tope 1', '320000.10')
  save()

  await screen.findByText('El período quedó guardado.')
  expect(bodies[0]).toMatchObject({
    estimated_income: '1450000.55',
    period_end: null,
    budgets: [{ limit_amount: '320000.10' }, { limit_amount: '80000' }],
  })
})

test('case C1-29: what was saved shows the computed end and offers to edit and confirm', async () => {
  apiWith([OCTOBER])
  saving(NOVEMBER)

  renderForm()

  await ready()
  save()

  await screen.findByText('El período quedó guardado.')
  expect(screen.getByText('del 10/11/2026 al 9/12/2026')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Editar' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Confirmar' })).toBeTruthy()
})

test('case C1-30: changing a draft replaces its content', async () => {
  apiWith([NOVEMBER, OCTOBER])
  const bodies: Record<string, unknown>[] = []
  const created = vi.fn()
  api.use(
    http.put(PERIOD, async ({ request, params }) => {
      expect(params.periodId).toBe(NOVEMBER.id)
      bodies.push((await request.json()) as Record<string, unknown>)
      return HttpResponse.json(NOVEMBER)
    }),
    http.post(PERIODS, () => {
      created()
      return HttpResponse.json(NOVEMBER, { status: 201 })
    }),
  )

  renderForm(NOVEMBER.id)

  await ready()
  type('Ingreso estimado', '1600000')
  save()

  await screen.findByText('El período quedó guardado.')
  expect(created).not.toHaveBeenCalled()
  expect(bodies).toEqual([
    {
      period_type: 'monthly',
      period_start: '2026-11-10',
      period_end: '2026-12-09',
      primary_currency: 'ARS',
      estimated_income: '1600000',
      budgets: [
        { category_id: SUPERMERCADO, limit_amount: '300000' },
        { category_id: TRANSPORTE, limit_amount: '80000' },
      ],
    },
  ])
})

test('case C1-31: confirming says since when it receives movements and goes back to that period', async () => {
  const confirmed = { ...NOVEMBER, status: 'confirmed' }
  let periods = [NOVEMBER, OCTOBER]
  const confirmedIds: unknown[] = []
  api.use(
    http.get(PERIODS, () => HttpResponse.json({ budget_periods: periods })),
    http.get(CATEGORIES, () => HttpResponse.json({ categories: CATEGORY_LIST })),
    http.put(PERIOD, () => HttpResponse.json(NOVEMBER)),
    http.post(CONFIRM, ({ params }) => {
      confirmedIds.push(params.periodId)
      periods = [confirmed, OCTOBER]
      return HttpResponse.json(confirmed)
    }),
    http.get(SUMMARY, ({ params }) =>
      HttpResponse.json({
        budget_period_id: params.periodId,
        primary_currency: 'ARS',
        estimated_income: 1500000,
        actual_income: 0,
        total_spent: 0,
        categories: [],
      }),
    ),
  )

  render(<BudgetPage onNoSession={nothing} />)

  // The summary opens the current period: the draft is chosen through the list.
  fireEvent.change(await screen.findByLabelText('Tus períodos existentes'), { target: { value: NOVEMBER.id } })
  fireEvent.click(await screen.findByRole('button', { name: 'Editar' }))
  await ready()
  save()
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

  await screen.findByText('El período quedó confirmado: recibe movimientos desde el 10/11/2026.')
  expect(confirmedIds).toEqual([NOVEMBER.id])
  fireEvent.click(screen.getByRole('button', { name: 'Volver al resumen' }))
  await waitFor(() => expect((screen.getByLabelText('Tus períodos existentes') as HTMLSelectElement).value).toBe(NOVEMBER.id))
})

test('case C1-32: in a confirmed period only the income and the limits are edited', async () => {
  apiWith([OCTOBER])
  const bodies: Record<string, unknown>[] = []
  api.use(
    http.put(PERIOD, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>)
      return HttpResponse.json(OCTOBER)
    }),
  )

  renderForm(OCTOBER.id)

  await ready()
  for (const label of ['Cadencia', 'Moneda', 'Inicio', 'Fin']) expect(field(label).disabled).toBe(true)
  expect(field('Ingreso estimado').disabled).toBe(false)
  expect(field('Monto del tope 1').disabled).toBe(false)
  type('Ingreso estimado', '1520000')
  save()

  await screen.findByText('El período quedó guardado.')
  expect(bodies[0]).toMatchObject({
    period_type: 'monthly',
    period_start: '2026-10-10',
    period_end: '2026-11-09',
    primary_currency: 'ARS',
    estimated_income: '1520000',
  })
  expect(screen.queryByRole('button', { name: 'Confirmar' })).toBeNull()
})

test('case C2-32: without categories it says so and saves without limits', async () => {
  apiWith([], [])
  const bodies = saving(NOVEMBER)

  renderForm()

  await screen.findByText('No hay categorías de gasto para ponerles tope')
  expect(screen.queryByRole('button', { name: 'Sumar un tope' })).toBeNull()
  type('Inicio', '2026-11-10')
  type('Moneda', 'ARS')
  type('Ingreso estimado', '0')
  save()

  await screen.findByText('El período quedó guardado.')
  expect(bodies[0]).toMatchObject({ primary_currency: 'ARS', budgets: [] })
})

test('case C2-33: if preparing the form fails retrying repeats only what failed', async () => {
  let categoryCalls = 0
  let periodCalls = 0
  api.use(
    http.get(CATEGORIES, () => {
      categoryCalls += 1
      return HttpResponse.json({ categories: CATEGORY_LIST })
    }),
    http.get(PERIODS, () => {
      periodCalls += 1
      return periodCalls === 1
        ? HttpResponse.json({ error: 'internal_error' }, { status: 500 })
        : HttpResponse.json({ budget_periods: [OCTOBER] })
    }),
  )

  renderForm()

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText('No se pudo preparar el formulario')).toBeTruthy()
  fireEvent.click(within(alert).getByRole('button', { name: 'Reintentar' }))

  await ready()
  expect(categoryCalls).toBe(1)
  expect(periodCalls).toBe(2)
})

test.each([
  ['a 500', 'La API respondió con un error.'],
  ['no answer in time', 'La API no respondió a tiempo.'],
])('case C2-34: if saving fails what was entered stays and retrying repeats it (%s)', async (failure, message) => {
  apiWith([OCTOBER])
  const bodies: unknown[] = []
  api.use(
    http.post(PERIODS, async ({ request }) => {
      bodies.push(await request.json())
      if (bodies.length > 1) return HttpResponse.json(NOVEMBER, { status: 201 })
      if (failure === 'a 500') return HttpResponse.json({ error: 'internal_error' }, { status: 500 })
      await delay('infinite')
      return HttpResponse.json({})
    }),
  )

  renderForm(null, nothing, SHORT_TIMEOUT_MS)

  await ready()
  type('Ingreso estimado', '1700000')
  save()

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText(message)).toBeTruthy()
  expect(field('Ingreso estimado').value).toBe('1700000')
  fireEvent.click(within(alert).getByRole('button', { name: 'Reintentar' }))

  await screen.findByText('El período quedó guardado.')
  expect(bodies).toHaveLength(2)
  expect(bodies[1]).toEqual(bodies[0])
})

test.each([
  ['not_found', 404, 'Ese período o una de sus categorías ya no está disponible.'],
  ['not_the_owner', 403, 'Solo el dueño del grupo puede cambiar este período.'],
  ['period_end_required', 422, 'Un período quincenal necesita una fecha de fin.'],
  ['period_dates_inverted', 422, 'La fecha de fin no puede ser anterior a la de inicio.'],
  ['confirmed_period_fixed', 409, 'Un período confirmado no cambia su cadencia, sus fechas ni su moneda.'],
  ['budget_period_overlap', 409, 'Estas fechas se superponen con otro de tus períodos: elegí otras.'],
  ['budget_limit_not_positive', 422, 'Cada tope tiene que ser mayor que cero.'],
  ['budget_category_repeated', 422, 'Elegiste la misma categoría en dos topes.'],
  ['budget_category_not_expense', 422, 'Un tope solo puede ir sobre una categoría de gasto.'],
  ['estimated_income_negative', 422, 'El ingreso estimado no puede ser negativo.'],
  ['currency_not_found', 422, 'Esa moneda no está disponible: elegí otra de la lista.'],
  ['amount_too_large', 422, 'Ese monto es demasiado grande.'],
  ['invalid_request', 422, 'Revisá los datos: falta alguno o tiene un valor que no es válido.'],
  ['a_code_it_does_not_know', 422, 'La API respondió con un error.'],
])('case C2-35: a refusal says what to correct without retrying (%s)', async (code, status, message) => {
  apiWith([OCTOBER])
  api.use(http.post(PERIODS, () => HttpResponse.json({ error: code }, { status })))

  renderForm()

  await ready()
  type('Ingreso estimado', '1700000')
  save()

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText(message)).toBeTruthy()
  expect(within(alert).queryByRole('button', { name: 'Reintentar' })).toBeNull()
  expect(field('Ingreso estimado').value).toBe('1700000')
  expect(field('Ingreso estimado').disabled).toBe(false)
  expect(screen.getByRole('button', { name: 'Guardar borrador' })).toBeTruthy()
})

test('case C2-36: if confirming fails retrying repeats only the confirmation', async () => {
  apiWith([OCTOBER])
  const bodies = saving(NOVEMBER)
  let confirmCalls = 0
  api.use(
    http.post(CONFIRM, async () => {
      confirmCalls += 1
      if (confirmCalls === 1) await delay('infinite')
      return HttpResponse.json({ ...NOVEMBER, status: 'confirmed' })
    }),
  )

  renderForm(null, nothing, SHORT_TIMEOUT_MS)

  await ready()
  save()
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText('La API no respondió a tiempo.')).toBeTruthy()
  expect(screen.getByText('del 10/11/2026 al 9/12/2026')).toBeTruthy()
  fireEvent.click(within(alert).getByRole('button', { name: 'Reintentar' }))

  await screen.findByText('El período quedó confirmado: recibe movimientos desde el 10/11/2026.')
  expect(confirmCalls).toBe(2)
  expect(bodies).toHaveLength(1)
})

test('case C2-37: without a session it goes back to the entry when preparing', async () => {
  api.use(
    http.get(PERIODS, () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })),
    http.get(CATEGORIES, () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })),
  )
  const onNoSession = vi.fn()

  renderForm(null, onNoSession)

  await waitFor(() => expect(onNoSession).toHaveBeenCalled())
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case C2-37: without a session it goes back to the entry when saving', async () => {
  apiWith([OCTOBER])
  api.use(http.post(PERIODS, () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })))
  const onNoSession = vi.fn()

  renderForm(null, onNoSession)

  await ready()
  save()

  await waitFor(() => expect(onNoSession).toHaveBeenCalled())
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case C2-37: without a session it goes back to the entry when confirming', async () => {
  apiWith([OCTOBER])
  saving(NOVEMBER)
  api.use(http.post(CONFIRM, () => HttpResponse.json({ error: 'unauthorized' }, { status: 401 })))
  const onNoSession = vi.fn()

  renderForm(null, onNoSession)

  await ready()
  save()
  fireEvent.click(await screen.findByRole('button', { name: 'Confirmar' }))

  await waitFor(() => expect(onNoSession).toHaveBeenCalled())
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case C2-38: a period that is no longer there says it is not available', async () => {
  apiWith([OCTOBER])

  renderForm(crypto.randomUUID())

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText('Ese período o una de sus categorías ya no está disponible.')).toBeTruthy()
  expect(within(alert).getByRole('button', { name: 'Volver al resumen' })).toBeTruthy()
  expect(screen.queryByLabelText('Inicio')).toBeNull()
})

test('case C2-43: the currency is chosen from the list of the catalog', async () => {
  apiWith([OCTOBER])
  const bodies = saving(NOVEMBER)

  renderForm()

  await ready()
  expect(field('Moneda').tagName).toBe('SELECT')
  expect(field('Moneda').value).toBe('ARS')
  const options = within(field('Moneda')).getAllByRole('option')
  expect(options.map((option) => option.textContent)).toEqual(['ARS — Peso argentino', 'USD — Dólar estadounidense'])
  type('Moneda', 'USD')
  save()

  await screen.findByText('El período quedó guardado.')
  expect(bodies[0]).toMatchObject({ primary_currency: 'USD' })
})

test('case C2-45: the status line says what it is doing and announces how it ended', async () => {
  apiWith([OCTOBER])
  saving(NOVEMBER)
  api.use(http.post(CONFIRM, () => HttpResponse.json({ ...NOVEMBER, status: 'confirmed' })))

  renderForm()

  await ready()
  save()
  expect(screen.getByRole('status').textContent).toBe('Guardando…')
  await waitFor(() => expect(screen.getByRole('status').textContent).toBe('El período quedó guardado.'))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
  expect(screen.getByRole('status').textContent).toBe('Confirmando…')
  await waitFor(() =>
    expect(screen.getByRole('status').textContent).toBe(
      'El período quedó confirmado: recibe movimientos desde el 10/11/2026.',
    ),
  )
})

test('case C2-46: if the dates overlap the notice shows the other periods', async () => {
  const home = period('2027-01-10', '2027-02-09', { family_group_id: crypto.randomUUID(), family_group_name: 'Casa' })
  apiWith([home, NOVEMBER, OCTOBER])
  api.use(http.post(PERIODS, () => HttpResponse.json({ error: 'budget_period_overlap' }, { status: 409 })))

  renderForm()

  await ready()
  type('Ingreso estimado', '1700000')
  save()

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText('Tus períodos')).toBeTruthy()
  expect(within(alert).getByText('del 10/10/2026 al 9/11/2026')).toBeTruthy()
  expect(within(alert).getByText('del 10/11/2026 al 9/12/2026')).toBeTruthy()
  expect(within(alert).queryByText('del 10/1/2027 al 9/2/2027')).toBeNull()
  expect(within(alert).queryByRole('button', { name: 'Reintentar' })).toBeNull()
  expect(field('Ingreso estimado').value).toBe('1700000')
})

test('case C2-46: when changing a period the notice does not show that same period', async () => {
  apiWith([NOVEMBER, OCTOBER])
  api.use(http.put(PERIOD, () => HttpResponse.json({ error: 'budget_period_overlap' }, { status: 409 })))

  renderForm(NOVEMBER.id)

  await ready()
  save()

  const alert = await screen.findByRole('alert')
  expect(within(alert).getByText('del 10/10/2026 al 9/11/2026')).toBeTruthy()
  expect(within(alert).queryByText('del 10/11/2026 al 9/12/2026')).toBeNull()
})

test('case C2-48: the limits are loaded with a single dropdown and go into a table', async () => {
  apiWith([OCTOBER])
  const bodies = saving(NOVEMBER)

  renderForm()

  await ready()
  expect(limitRows().map((row) => within(row).getByRole('rowheader').textContent)).toEqual([
    'Supermercado',
    'Transporte',
  ])
  expect(within(limitRows()[0]).getByRole('button', { name: 'Quitar el tope 1' })).toBeTruthy()
  expect(offered()).toEqual(['Salud'])

  addLimit()
  expect(screen.getByText('Poné un monto para sumar el tope.')).toBeTruthy()
  expect(limitRows()).toHaveLength(2)

  type('Monto del tope nuevo', '40000')
  addLimit()
  expect(limitRows()).toHaveLength(3)
  expect(screen.queryByText('Poné un monto para sumar el tope.')).toBeNull()
  expect(screen.getByText('Ya tienen tope todas tus categorías')).toBeTruthy()
  expect(screen.queryByLabelText('Categoría del tope nuevo')).toBeNull()

  type('Monto del tope 1', '320000')
  fireEvent.click(screen.getByRole('button', { name: 'Quitar el tope 2' }))
  expect(offered()).toEqual(['Transporte'])
  expect(screen.queryByText('Ya tienen tope todas tus categorías')).toBeNull()
  save()

  await screen.findByText('El período quedó guardado.')
  expect(bodies[0].budgets).toEqual([
    { category_id: SUPERMERCADO, limit_amount: '320000' },
    { category_id: SALUD, limit_amount: '40000' },
  ])
})

test.each(['Ingreso estimado', 'Monto del tope nuevo', 'Monto del tope 1'])(
  'case C2-49: the amount fields take only digits and one decimal separator (%s)',
  async (label) => {
    apiWith([OCTOBER])

    renderForm()

    await ready()
    for (const [written, kept] of [
      ['12a', '12'],
      ['-500', '500'],
      ['1e30', '130'],
      ['1450000,55', '1450000,55'],
      ['1.450.000', '1.450000'],
    ]) {
      type(label, written)
      expect(field(label).value).toBe(kept)
    }
    expect(screen.getAllByText('Sin puntos de miles. Para los centavos usá coma: 1450000,55')).toHaveLength(2)
  },
)
