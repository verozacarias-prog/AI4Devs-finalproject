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
} as const satisfies Record<string, keyof paths>

/** The answer of a health route when everything is fine. */
export const HEALTH_OK: components['schemas']['HealthState'] = 'ok'
