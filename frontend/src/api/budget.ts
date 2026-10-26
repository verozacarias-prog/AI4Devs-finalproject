import { HTTP_UNAUTHORIZED } from '../constants'
import { request, type Failure, type Options } from './request'
import { API_ROUTES, fillRoute } from './routes'
import type { components } from './schema'

export type BudgetPeriod = components['schemas']['BudgetPeriodItem']
export type PeriodSummary = components['schemas']['PeriodSummaryBody']
export type CategorySpending = components['schemas']['CategorySpendingItem']
export type BudgetStatus = components['schemas']['BudgetStatusBody']
export type BudgetMovement = components['schemas']['BudgetMovementItem']
type BudgetPeriodList = components['schemas']['BudgetPeriodList']

export type Loaded<T> = { kind: 'loaded'; value: T } | { kind: 'no-session' } | Failure

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
