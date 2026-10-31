import { HTTP_SERVER_ERROR, HTTP_UNAUTHORIZED } from '../constants'
import { request, type Failure, type Options } from './request'
import { API_ROUTES, fillRoute } from './routes'
import type { components } from './schema'

export type BudgetPeriod = components['schemas']['BudgetPeriodItem']
export type PeriodSummary = components['schemas']['PeriodSummaryBody']
export type CategorySpending = components['schemas']['CategorySpendingItem']
export type BudgetStatus = components['schemas']['BudgetStatusBody']
export type BudgetMovement = components['schemas']['BudgetMovementItem']
export type Category = components['schemas']['CategoryItem']
export type PeriodContent = components['schemas']['BudgetPeriodRequest']
type BudgetPeriodList = components['schemas']['BudgetPeriodList']
type CategoryList = components['schemas']['CategoryList']
type ErrorBody = components['schemas']['ErrorBody']

export type Loaded<T> = { kind: 'loaded'; value: T } | { kind: 'no-session' } | Failure

/** One write: the period as the API left it, or the code of the rule that refused it. */
export type Saved =
  | { kind: 'saved'; value: BudgetPeriod }
  | { kind: 'refused'; code: string }
  | { kind: 'no-session' }
  | Failure

/** One read of the budget: what the API computed, or why there is nothing. */
async function load<T>(path: string, options: Options): Promise<Loaded<T>> {
  const answer = await request(path, options)
  if (answer.kind !== 'answered') return answer
  if (answer.status === HTTP_UNAUTHORIZED) return { kind: 'no-session' }
  if (!answer.ok) return { kind: 'api-error' }
  return { kind: 'loaded', value: answer.body as T }
}

/** The periods the user can read, in the order the screen shows them (GET /budget-periods). */
export async function loadBudgetPeriods(options: Options = {}): Promise<Loaded<BudgetPeriod[]>> {
  const loaded = await load<BudgetPeriodList>(API_ROUTES.budgetPeriods, options)
  return loaded.kind === 'loaded' ? { kind: 'loaded', value: loaded.value.budget_periods } : loaded
}

/** The incomes of a period and what each category spent (GET /budget-periods/{period_id}/summary). */
export function loadPeriodSummary(periodId: string, options: Options = {}): Promise<Loaded<PeriodSummary>> {
  return load(fillRoute(API_ROUTES.budgetPeriodSummary, { period_id: periodId }), options)
}

/** One limit with the movements that count in it (GET /budgets/{budget_id}). */
export function loadBudgetStatus(budgetId: string, options: Options = {}): Promise<Loaded<BudgetStatus>> {
  return load(fillRoute(API_ROUTES.budget, { budget_id: budgetId }), options)
}

/** The expense categories the user can put a limit on, by name (GET /categories). */
export async function loadCategories(options: Options = {}): Promise<Loaded<Category[]>> {
  const loaded = await load<CategoryList>(API_ROUTES.categories, options)
  return loaded.kind === 'loaded' ? { kind: 'loaded', value: loaded.value.categories } : loaded
}

/** Builds a draft, or replaces the content of that period (POST and PUT /budget-periods). */
export function savePeriod(content: PeriodContent, periodId: string | null, options: Options = {}): Promise<Saved> {
  return periodId === null
    ? write(API_ROUTES.budgetPeriods, { ...options, method: 'POST', body: content })
    : write(fillRoute(API_ROUTES.budgetPeriod, { period_id: periodId }), { ...options, method: 'PUT', body: content })
}

/** Confirms a draft (POST /budget-periods/{period_id}/confirm). */
export function confirmPeriod(periodId: string, options: Options = {}): Promise<Saved> {
  return write(fillRoute(API_ROUTES.budgetPeriodConfirm, { period_id: periodId }), { ...options, method: 'POST' })
}

async function write(path: string, call: Options & { method: 'POST' | 'PUT'; body?: PeriodContent }): Promise<Saved> {
  const answer = await request(path, call)
  if (answer.kind !== 'answered') return answer
  if (answer.status === HTTP_UNAUTHORIZED) return { kind: 'no-session' }
  if (answer.ok) return { kind: 'saved', value: answer.body as BudgetPeriod }
  if (answer.status >= HTTP_SERVER_ERROR || answer.body === null) return { kind: 'api-error' }
  return { kind: 'refused', code: (answer.body as ErrorBody).error }
}
