import { API_ROUTES } from './routes'
import type { components } from './schema'

type HealthStatus = components['schemas']['HealthStatus']

/** What the dashboard can find out about the system from the readiness route. */
export type Readiness =
  | { kind: 'ready' }
  | { kind: 'database-unreachable' }
  | { kind: 'api-unreachable' }

/**
 * Asks the API whether it reaches the database (GET /readyz, docs/04-api.md).
 * Never throws: a network failure is one of the answers.
 */
export async function checkReadiness(): Promise<Readiness> {
  let response: Response
  try {
    response = await fetch(API_ROUTES.readyz, { headers: { Accept: 'application/json' } })
  } catch {
    return { kind: 'api-unreachable' }
  }
  if (response.status === 503) {
    return { kind: 'database-unreachable' }
  }
  if (!response.ok) {
    return { kind: 'api-unreachable' }
  }
  try {
    const body = (await response.json()) as HealthStatus
    return body.status === 'ok' ? { kind: 'ready' } : { kind: 'database-unreachable' }
  } catch {
    return { kind: 'api-unreachable' }
  }
}
