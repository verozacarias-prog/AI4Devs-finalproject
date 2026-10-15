import { HTTP_UNAUTHORIZED } from '../constants'
import { request, type Failure, type Options } from './request'
import { API_ROUTES } from './routes'
import type { components } from './schema'

export type Account = components['schemas']['AccountItem']
type AccountList = components['schemas']['AccountList']

export type Accounts = { kind: 'loaded'; accounts: Account[] } | { kind: 'no-session' } | Failure

/**
 * The accounts of the user of the session, with the balance the API computed (GET /accounts,
 * docs/04-api.md). They come already in the order the screen shows them.
 */
export async function loadAccounts(options: Options = {}): Promise<Accounts> {
  const answer = await request(API_ROUTES.accounts, options)
  if (answer.kind !== 'answered') return answer
  if (answer.status === HTTP_UNAUTHORIZED) return { kind: 'no-session' }
  if (!answer.ok) return { kind: 'api-error' }
  return { kind: 'loaded', accounts: (answer.body as AccountList).accounts }
}
