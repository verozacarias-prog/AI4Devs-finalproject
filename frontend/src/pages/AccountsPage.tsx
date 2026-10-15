import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
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
    <Card aria-labelledby="accounts-heading">
      <CardTitle id="accounts-heading" className="text-xl">
        {TEXT.heading}
      </CardTitle>
      <p ref={statusLine} role="status" tabIndex={-1} className="text-sm text-muted-foreground outline-none empty:hidden">
        {state.kind === 'loading' ? TEXT.loading : state.kind === 'empty' ? TEXT.empty : ''}
      </p>
      {state.kind === 'content' && (
        <div className="flex flex-col gap-6">
          {state.groups.map((group) => (
            <section key={group.currency} aria-labelledby={`group-${group.currency}`}>
              <GroupHeading id={`group-${group.currency}`}>{TEXT.currencyGroup(group.currency)}</GroupHeading>
              <AccountRows accounts={group.accounts} />
            </section>
          ))}
          {state.investments.length > 0 && (
            <section aria-labelledby="group-investments">
              <GroupHeading id="group-investments">{TEXT.investmentsHeading}</GroupHeading>
              <CardDescription className="mb-2">{TEXT.investmentsDetail}</CardDescription>
              <AccountRows accounts={state.investments} />
            </section>
          )}
        </div>
      )}
      {state.kind === 'empty' && <CardDescription>{TEXT.emptyDetail}</CardDescription>}
      {state.kind === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="font-semibold text-destructive">{TEXT.failed}</p>
          <p className="text-sm text-muted-foreground">{ERROR_MESSAGES[state.cause]}</p>
          <Button onClick={retry}>{MESSAGES.common.retry}</Button>
        </div>
      )}
    </Card>
  )
}

function GroupHeading({ id, children }: { id: string; children: string }) {
  return (
    <h3 id={id} className="mb-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
      {children}
    </h3>
  )
}

/**
 * The `account…` class names have no style of their own: the tests of this screen find a row,
 * its name and its amount by them. Do not remove them as unused.
 */
function AccountRows({ accounts }: { accounts: Account[] }) {
  return (
    <ul className="divide-y rounded-lg border">
      {accounts.map((account) => (
        <li key={account.id} className="account flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
          <span className="account__name font-medium">{account.name}</span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {account.balance_kind === 'net_contributed' ? TEXT.netContributed : TEXT.types[account.type]}
          </span>
          <span
            className={cn(
              'account__amount ml-auto font-semibold tabular-nums',
              account.balance < 0 && 'account__amount--negative text-destructive',
            )}
          >
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
