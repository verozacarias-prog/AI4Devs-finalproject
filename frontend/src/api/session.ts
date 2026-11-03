import { HTTP_CONFLICT, HTTP_NOT_FOUND, HTTP_UNAUTHORIZED } from '../constants'
import { request, type Failure, type Options } from './request'
import { API_ROUTES } from './routes'
import type { components } from './schema'

export type SessionUser = components['schemas']['Me']
export type DevUser = components['schemas']['DevUser']
type DevUsers = components['schemas']['DevUsers']
type DevSessionRequest = components['schemas']['DevSessionRequest']
type TestNoticeRequired = components['schemas']['TestNoticeRequired']

/** What entering with a personal link can end in, besides a failure. */
export type LinkEntry =
  | { kind: 'entered' }
  /** The link has no user yet: the person has to accept this version of the test notice. */
  | { kind: 'notice-required'; version: string }
  /** The link does not exist or was regenerated. */
  | { kind: 'link-rejected' }
  | Failure

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

/**
 * Opens the session of a personal link (POST /dev/session, ADR 0016). The value travels in the
 * body, never in the address the server sees.
 */
export async function enterWithLink(
  value: string,
  acceptedNotice: string | null,
  options: Options = {},
): Promise<LinkEntry> {
  const body: DevSessionRequest = { access_token: value }
  if (acceptedNotice !== null) body.accept_test_notice = acceptedNotice
  const answer = await request(API_ROUTES.devSession, { ...options, method: 'POST', body })
  if (answer.kind !== 'answered') return answer
  if (answer.ok) return { kind: 'entered' }
  if (answer.status === HTTP_NOT_FOUND) return { kind: 'link-rejected' }
  const version = noticeVersion(answer.body)
  if (answer.status === HTTP_CONFLICT && version !== null) return { kind: 'notice-required', version }
  return { kind: 'api-error' }
}

/** The version of the notice in a 409, or null when the answer is some other conflict. */
function noticeVersion(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('notice_version' in body)) return null
  const version: unknown = (body as Partial<TestNoticeRequired>).notice_version
  return typeof version === 'string' && version !== '' ? version : null
}

/** Closes the session of this browser (POST /auth/logout). */
export function logout(options: Options = {}): Promise<{ kind: 'closed' } | Failure> {
  return close(API_ROUTES.logout, options)
}

/** Closes every session of the user, on all their devices (POST /auth/logout-all). */
export function logoutAll(options: Options = {}): Promise<{ kind: 'closed' } | Failure> {
  return close(API_ROUTES.logoutAll, options)
}

async function close(route: string, options: Options): Promise<{ kind: 'closed' } | Failure> {
  const answer = await request(route, { ...options, method: 'POST' })
  if (answer.kind !== 'answered') return answer
  // Without a valid session there is nothing left to close, which is what was asked for.
  return answer.ok || answer.status === HTTP_UNAUTHORIZED ? { kind: 'closed' } : { kind: 'api-error' }
}
