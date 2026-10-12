/**
 * The paths of the API the dashboard calls, in one place. They are relative: the dashboard
 * and the API share one origin (ADR 0016).
 */
export const API_ROUTES = {
  healthz: '/healthz',
  readyz: '/readyz',
} as const
