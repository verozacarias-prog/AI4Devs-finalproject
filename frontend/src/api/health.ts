import { API_TIMEOUT_MS, HTTP_SERVICE_UNAVAILABLE, JSON_CONTENT_TYPE } from '../constants'
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
  | { kind: 'cancelled' }

type Options = {
  /** How long to wait for the whole answer, body included. */
  timeoutMs?: number
  /** Lets the caller abandon the request, for example when its screen goes away. */
  signal?: AbortSignal
}

/**
 * Asks the API whether it reaches the database (GET /readyz, docs/04-api.md).
 * Never throws: every failure is one of the answers.
 */
export async function checkReadiness({
  timeoutMs = API_TIMEOUT_MS,
  signal,
}: Options = {}): Promise<Readiness> {
  const timeout = AbortSignal.timeout(timeoutMs)
  const stop = AbortSignal.any(signal ? [timeout, signal] : [timeout])
  // Rejects when the request has to stop. Reading the body races against it, because not
  // every environment interrupts a body that is already arriving.
  const stopped = new Promise<never>((_, reject) => {
    stop.addEventListener('abort', () => reject(stop.reason), { once: true })
  })
  stopped.catch(() => {})

  // Why a request or the reading of its body stopped, when it was not the network.
  const interruption = (): Readiness | null => {
    if (signal?.aborted) return { kind: 'cancelled' }
    if (timeout.aborted) return { kind: 'api-timeout' }
    return null
  }

  let response: Response
  try {
    response = await fetch(API_ROUTES.readyz, {
      headers: { Accept: JSON_CONTENT_TYPE },
      signal: stop,
    })
  } catch {
    return interruption() ?? { kind: 'api-unreachable' }
  }
  if (response.status === HTTP_SERVICE_UNAVAILABLE) {
    return { kind: 'database-unreachable' }
  }
  if (!response.ok) {
    return { kind: 'api-error' }
  }
  try {
    const body = (await Promise.race([response.json(), stopped])) as HealthStatus
    return { kind: body.status === HEALTH_OK ? 'ready' : 'database-unreachable' }
  } catch {
    return interruption() ?? { kind: 'api-error' }
  }
}
