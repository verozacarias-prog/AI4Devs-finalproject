import { API_TIMEOUT_MS, JSON_CONTENT_TYPE } from '../constants'

/** Why the API gave no usable answer. */
export type Failure =
  | { kind: 'api-error' }
  | { kind: 'api-timeout' }
  | { kind: 'api-unreachable' }
  | { kind: 'cancelled' }

export type Answer = { kind: 'answered'; status: number; ok: boolean; body: unknown } | Failure

export type Options = {
  /** How long to wait for the whole answer, body included. */
  timeoutMs?: number
  /** Lets the caller abandon the request, for example when its screen goes away. */
  signal?: AbortSignal
}

type Call = Options & {
  method?: 'GET' | 'POST'
  /** Sent as JSON. A POST without it still declares JSON, which the API requires. */
  body?: unknown
}

/**
 * One call to the API. Never throws: every failure is one of the answers. The session
 * travels in a cookie the page cannot read, and the browser sends it by itself because the
 * dashboard and the API share one origin (ADR 0016).
 */
export async function request(
  path: string,
  { method = 'GET', body, timeoutMs = API_TIMEOUT_MS, signal }: Call = {},
): Promise<Answer> {
  const timeout = AbortSignal.timeout(timeoutMs)
  const stop = AbortSignal.any(signal ? [timeout, signal] : [timeout])
  // Rejects when the request has to stop. Reading the body races against it, because not
  // every environment interrupts a body that is already arriving. The listener is also what
  // keeps the combined signal alive until then.
  const stopped = new Promise<never>((_, reject) => {
    stop.addEventListener('abort', () => reject(stop.reason), { once: true })
  })
  stopped.catch(() => {})
  const interruption = (): Failure | null => {
    if (signal?.aborted) return { kind: 'cancelled' }
    if (timeout.aborted) return { kind: 'api-timeout' }
    return null
  }

  const headers: Record<string, string> = { Accept: JSON_CONTENT_TYPE }
  if (method === 'POST') headers['Content-Type'] = JSON_CONTENT_TYPE

  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers,
      body: method === 'POST' ? JSON.stringify(body ?? {}) : undefined,
      signal: stop,
    })
  } catch {
    return interruption() ?? { kind: 'api-unreachable' }
  }
  const isJson = response.headers.get('Content-Type')?.startsWith(JSON_CONTENT_TYPE) ?? false
  if (!isJson) {
    return { kind: 'answered', status: response.status, ok: response.ok, body: null }
  }
  try {
    const answered: unknown = await Promise.race([response.json(), stopped])
    return { kind: 'answered', status: response.status, ok: response.ok, body: answered }
  } catch {
    return interruption() ?? { kind: 'api-error' }
  }
}
