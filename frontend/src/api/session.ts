import { HTTP_NOT_FOUND, HTTP_UNAUTHORIZED } from '../constants'
import { request, type Failure, type Options } from './request'
import { API_ROUTES } from './routes'
import type { components } from './schema'

export type SessionUser = components['schemas']['Me']
export type DevUser = components['schemas']['DevUser']
type DevUsers = components['schemas']['DevUsers']
type DevSessionRequest = components['schemas']['DevSessionRequest']

/** Where a person stands when the entry screen opens. */
export type Entry =
  | { kind: 'signed-in'; user: SessionUser }
  | { kind: 'choose'; users: DevUser[] }
  /** The development entry is off, or this environment has no list of users. */
  | { kind: 'unavailable' }
  | Failure

/**
 * Asks who is behind the session (GET /me) and, when there is none, which test users can be
 * chosen (GET /dev/users, docs/04-api.md).
 */
export async function loadEntry(options: Options = {}): Promise<Entry> {
  const me = await request(API_ROUTES.me, options)
  if (me.kind !== 'answered') return me
  if (me.ok) return { kind: 'signed-in', user: me.body as SessionUser }
  if (me.status !== HTTP_UNAUTHORIZED) return { kind: 'api-error' }

  const users = await request(API_ROUTES.devUsers, options)
  if (users.kind !== 'answered') return users
  if (users.status === HTTP_NOT_FOUND) return { kind: 'unavailable' }
  if (!users.ok) return { kind: 'api-error' }
  return { kind: 'choose', users: (users.body as DevUsers).users }
}

/** Opens a session for that test user (POST /dev/session). The cookie arrives by itself. */
export async function enterAs(
  userId: string,
  options: Options = {},
): Promise<{ kind: 'entered' } | Failure> {
  const body: DevSessionRequest = { user_id: userId }
  const answer = await request(API_ROUTES.devSession, { ...options, method: 'POST', body })
  if (answer.kind !== 'answered') return answer
  return answer.ok ? { kind: 'entered' } : { kind: 'api-error' }
}

/** Closes the session of this browser (POST /auth/logout). */
export async function logout(options: Options = {}): Promise<{ kind: 'closed' } | Failure> {
  const answer = await request(API_ROUTES.logout, { ...options, method: 'POST' })
  if (answer.kind !== 'answered') return answer
  // Without a valid session there is nothing left to close, which is what was asked for.
  return answer.ok || answer.status === HTTP_UNAUTHORIZED ? { kind: 'closed' } : { kind: 'api-error' }
}
