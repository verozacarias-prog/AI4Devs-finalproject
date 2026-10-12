import { API_TIMEOUT_MS, HTTP_SERVICE_UNAVAILABLE } from '../constants'
import { API_ROUTES, HEALTH_OK } from './routes'
import type { components } from './schema'

type HealthStatus = components['schemas']['HealthStatus']

/** What the dashboard can find out about the system from the readiness route. */
export type Readiness =
  | { kind: 'ready' }
  | { kind: 'database-unreachable' }
  | { kind: 'api-error' }
  | { kind: 'api-timeout' }
  | { kind: 'api-unreachable' }

/**
 * Asks the API whether it reaches the database (GET /readyz, docs/04-api.md).
 * Never throws: every failure is one of the answers.
 */
export async function checkReadiness(timeoutMs: number = API_TIMEOUT_MS): Promise<Readiness> {
  const timeout = AbortSignal.timeout(timeoutMs)
  let response: Response
  try {
    response = await fetch(API_ROUTES.readyz, {
      headers: { Accept: 'application/json' },
      signal: timeout,
    })
  } catch {
    return { kind: timeout.aborted ? 'api-timeout' : 'api-unreachable' }
  }
  if (response.status === HTTP_SERVICE_UNAVAILABLE) {
    return { kind: 'database-unreachable' }
  }
  if (!response.ok) {
    return { kind: 'api-error' }
  }
  try {
    const body = (await response.json()) as HealthStatus
    return { kind: body.status === HEALTH_OK ? 'ready' : 'database-unreachable' }
  } catch {
    return { kind: 'api-error' }
  }
}
