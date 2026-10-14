import { useEffect, useRef, useState } from 'react'
import { loadAccounts, type Account } from '../api/accounts'
import type { Failure } from '../api/request'
import { AMOUNT_DECIMALS, AMOUNT_LOCALE } from '../constants'
import { MESSAGES } from '../messages'

/**
 * The accounts of the user with their balance (FEAT-001). The four states of a screen
 * (docs/convenciones-de-desarrollo.md, section 2). The screen only shows what the API
 * computed: it adds nothing, converts nothing and rounds nothing.
 */
type State =
  | { kind: 'loading' }
  | { kind: 'content'; groups: Group[]; investments: Account[] }
  | { kind: 'empty' }
  | { kind: 'error'; cause: ErrorCause }

type ErrorCause = Exclude<Failure['kind'], 'cancelled'>

type Group = { currency: string; accounts: Account[] }

const TEXT = MESSAGES.accounts

const ERROR_MESSAGES: Record<ErrorCause, string> = MESSAGES.common.apiFailures

type Props = {
  /** Called when the API says there is no session: the entry is shown again. */
  onNoSession: () => void
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
}

export function AccountsPage({ onNoSession, timeoutMs }: Props) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)
  // Always mounted, so a screen reader announces each change and the focus has where to go
  // when the retry button disappears.
  const statusLine = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    const abandon = new AbortController()
    void loadAccounts({ timeoutMs, signal: abandon.signal }).then((loaded) => {
      if (abandon.signal.aborted || loaded.kind === 'cancelled') return
      if (loaded.kind === 'no-session') {
        onNoSession()
        return
      }
      setState(loaded.kind === 'loaded' ? arrange(loaded.accounts) : { kind: 'error', cause: loaded.kind })
    })
    return () => abandon.abort()
  }, [attempt, timeoutMs, onNoSession])

  function retry() {
    setState({ kind: 'loading' })
    setAttempt((current) => current + 1)
    statusLine.current?.focus()
  }

  return (
    <section className="card" aria-labelledby="accounts-heading">
      <h2 id="accounts-heading" className="card__heading">
        {TEXT.heading}
      </h2>
      <p ref={statusLine} role="status" tabIndex={-1} className="card__text">
        {state.kind === 'loading' ? TEXT.loading : state.kind === 'empty' ? TEXT.empty : ''}
      </p>
      {state.kind === 'content' && (
        <>
          {state.groups.map((group) => (
            <section key={group.currency} className="account-group" aria-labelledby={`group-${group.currency}`}>
              <h3 id={`group-${group.currency}`} className="account-group__heading">
                {TEXT.currencyGroup(group.currency)}
              </h3>
              <AccountRows accounts={group.accounts} />
            </section>
          ))}
          {state.investments.length > 0 && (
            <section className="account-group" aria-labelledby="group-investments">
              <h3 id="group-investments" className="account-group__heading">
                {TEXT.investmentsHeading}
              </h3>
              <p className="card__text">{TEXT.investmentsDetail}</p>
              <AccountRows accounts={state.investments} />
            </section>
          )}
        </>
      )}
      {state.kind === 'empty' && <p className="card__text">{TEXT.emptyDetail}</p>}
      {state.kind === 'error' && (
        <div role="alert">
          <p className="status status--error">{TEXT.failed}</p>
          <p className="card__text">{ERROR_MESSAGES[state.cause]}</p>
          <button type="button" className="button" onClick={retry}>
            {MESSAGES.common.retry}
          </button>
        </div>
      )}
    </section>
  )
}

function AccountRows({ accounts }: { accounts: Account[] }) {
  return (
    <ul className="accounts">
      {accounts.map((account) => (
        <li key={account.id} className="account">
          <span className="account__name">{account.name}</span>
          <span className="account__type">
            {account.balance_kind === 'net_contributed' ? TEXT.netContributed : TEXT.types[account.type]}
          </span>
          <span className={account.balance < 0 ? 'account__amount account__amount--negative' : 'account__amount'}>
            {formatAmount(account.balance, account.currency)}
          </span>
        </li>
      ))}
    </ul>
  )
}

/**
 * Splits what the API sent, in its order: the accounts by currency, the investment ones
 * apart, and the ones others owe left out (domain rules, § 16). Nothing is added up.
 */
function arrange(accounts: Account[]): State {
  const groups: Group[] = []
  const investments: Account[] = []
  for (const account of accounts) {
    if (account.type === 'receivable') continue
    if (account.balance_kind === 'net_contributed') {
      investments.push(account)
      continue
    }
    const group = groups.find((candidate) => candidate.currency === account.currency)
    if (group) group.accounts.push(account)
    else groups.push({ currency: account.currency, accounts: [account] })
  }
  if (groups.length === 0 && investments.length === 0) return { kind: 'empty' }
  return { kind: 'content', groups, investments }
}

/** Writes an amount with its currency, so it is never read as a bare number. */
function formatAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat(AMOUNT_LOCALE, {
    style: 'currency',
    currency,
    minimumFractionDigits: AMOUNT_DECIMALS,
    maximumFractionDigits: AMOUNT_DECIMALS,
  }).format(amount)
}
