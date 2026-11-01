import type { components, paths } from './schema.d.ts'

/**
 * The paths of the API the dashboard calls, in one place. They are relative: the dashboard
 * and the API share one origin (ADR 0016). Each one has to exist in the generated contract,
 * so renaming a route in the API stops the dashboard from compiling.
 */
export const API_ROUTES = {
  healthz: '/healthz',
  readyz: '/readyz',
  me: '/me',
  logout: '/auth/logout',
  devUsers: '/dev/users',
  devSession: '/dev/session',
  accounts: '/accounts',
  budgetPeriods: '/budget-periods',
  budgetPeriod: '/budget-periods/{period_id}',
  budgetPeriodConfirm: '/budget-periods/{period_id}/confirm',
  budgetPeriodSummary: '/budget-periods/{period_id}/summary',
  categories: '/categories',
  currencies: '/currencies',
  budget: '/budgets/{budget_id}',
  chatMessages: '/chat/messages',
} as const satisfies Record<string, keyof paths>

/** A route with its `{name}` parameters filled in, each one escaped. */
export function fillRoute(route: string, parameters: Record<string, string>): string {
  return route.replace(/\{(\w+)\}/g, (_, name: string) => encodeURIComponent(parameters[name] ?? ''))
}

/** The answer of a health route when everything is fine. */
export const HEALTH_OK: components['schemas']['HealthState'] = 'ok'
