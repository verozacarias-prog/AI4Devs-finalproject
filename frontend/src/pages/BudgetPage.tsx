import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/class-names'
import {
  loadBudgetPeriods,
  loadBudgetStatus,
  loadPeriodSummary,
  type BudgetMovement,
  type BudgetPeriod,
  type BudgetStatus,
  type CategorySpending,
  type Loaded,
  type PeriodSummary,
} from '../api/budget'
import type { Failure } from '../api/request'
import {
  AMOUNT_DECIMALS,
  AMOUNT_LOCALE,
  DATE_FORMAT,
  DATE_LOCALE,
  DATE_TIME_ZONE,
  EXCHANGE_RATE_MAX_DECIMALS,
  NEAR_LIMIT_PERCENTAGE,
  OVER_LIMIT_PERCENTAGE,
  PERCENTAGE_DECIMALS,
} from '../constants'
import { MESSAGES } from '../messages'

/**
 * The budget of a period: its incomes, what each category spent, and the movements of one
 * limit (FEAT-004). The screen only shows what the API computed: it adds nothing, converts
 * nothing and rounds nothing. The only thing it decides is the state of each bar.
 */
type View =
  | { kind: 'loading' }
  // The user has no period at all.
  | { kind: 'no-periods' }
  | { kind: 'summary'; summary: PeriodSummary }
  | { kind: 'detail'; status: BudgetStatus }
  | { kind: 'error'; cause: ErrorCause }

type ErrorCause = Exclude<Failure['kind'], 'cancelled'>

/** What the screen is showing of the chosen period: its summary, or the detail of a limit. */
type Showing = { kind: 'summary' } | { kind: 'detail'; budgetId: string }

type BarState = 'normal' | 'near' | 'over'

const TEXT = MESSAGES.budget

type Props = {
  /** Called when the API says there is no session: the entry is shown again. */
  onNoSession: () => void
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
}

export function BudgetPage({ onNoSession, timeoutMs }: Props) {
  const [periods, setPeriods] = useState<BudgetPeriod[] | null>(null)
  const [periodId, setPeriodId] = useState<string | null>(null)
  const [showing, setShowing] = useState<Showing>({ kind: 'summary' })
  const [view, setView] = useState<View>({ kind: 'loading' })
  // Retrying repeats only the query that failed: the periods, or what is shown of one.
  const [periodsAttempt, setPeriodsAttempt] = useState(0)
  const [viewAttempt, setViewAttempt] = useState(0)
  const statusLine = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    const abandon = new AbortController()
    void loadBudgetPeriods({ timeoutMs, signal: abandon.signal }).then((loaded) => {
      if (abandon.signal.aborted || loaded.kind === 'cancelled') return
      if (loaded.kind === 'no-session') return onNoSession()
      if (loaded.kind !== 'loaded') return setView({ kind: 'error', cause: loaded.kind })
      setPeriods(loaded.value)
      if (loaded.value.length === 0) return setView({ kind: 'no-periods' })
      setPeriodId(opening(loaded.value)?.id ?? null)
    })
    return () => abandon.abort()
  }, [periodsAttempt, timeoutMs, onNoSession])

  useEffect(() => {
    if (periodId === null) return
    const abandon = new AbortController()
    const options = { timeoutMs, signal: abandon.signal }
    const show = <T,>(loaded: Loaded<T>, toView: (value: T) => View) => {
      if (abandon.signal.aborted || loaded.kind === 'cancelled') return
      if (loaded.kind === 'no-session') return onNoSession()
      setView(loaded.kind === 'loaded' ? toView(loaded.value) : { kind: 'error', cause: loaded.kind })
    }
    if (showing.kind === 'summary') {
      void loadPeriodSummary(periodId, options).then((loaded) =>
        show(loaded, (summary) => ({ kind: 'summary', summary })),
      )
    } else {
      void loadBudgetStatus(showing.budgetId, options).then((loaded) =>
        show(loaded, (status) => ({ kind: 'detail', status })),
      )
    }
    return () => abandon.abort()
  }, [periodId, showing, viewAttempt, timeoutMs, onNoSession])

  function choosePeriod(id: string) {
    setView({ kind: 'loading' })
    setShowing({ kind: 'summary' })
    setPeriodId(id)
  }

  function show(next: Showing) {
    setView({ kind: 'loading' })
    setShowing(next)
  }

  function retry() {
    setView({ kind: 'loading' })
    if (periods === null) setPeriodsAttempt((current) => current + 1)
    else setViewAttempt((current) => current + 1)
    statusLine.current?.focus()
  }

  const chosen = periods?.find((candidate) => candidate.id === periodId)

  return (
    <Card aria-labelledby="budget-heading">
      <CardTitle id="budget-heading" className="text-xl">
        {TEXT.heading}
      </CardTitle>
      {periods && periods.length > 0 && (
        <label className="flex flex-col gap-1 text-sm font-medium">
          {TEXT.period}
          <select
            value={periodId ?? ''}
            onChange={(event) => choosePeriod(event.target.value)}
            className="rounded-md border bg-card px-3 py-2 outline-none focus-visible:ring-(length:--focus-ring-width) focus-visible:ring-ring"
          >
            {periods.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {periodLabel(candidate)}
              </option>
            ))}
          </select>
        </label>
      )}
      <p ref={statusLine} role="status" tabIndex={-1} className="text-sm text-muted-foreground outline-none empty:hidden">
        {view.kind === 'loading' ? TEXT.loading : ''}
      </p>
      {view.kind === 'no-periods' && (
        <div className="flex flex-col gap-1">
          <h3 className="text-sm font-medium">{TEXT.noPeriods}</h3>
          <CardDescription>{TEXT.noPeriodsDetail}</CardDescription>
        </div>
      )}
      {chosen?.status === 'draft' && view.kind !== 'loading' && view.kind !== 'error' && (
        <p className="rounded-lg border border-warning bg-warning/15 px-4 py-3 text-sm">{TEXT.draftNotice}</p>
      )}
      {view.kind === 'summary' && (
        <Summary summary={view.summary} onOpen={(budgetId) => show({ kind: 'detail', budgetId })} />
      )}
      {view.kind === 'detail' && <Detail status={view.status} onBack={() => show({ kind: 'summary' })} />}
      {view.kind === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-2">
          <p className="font-semibold text-destructive">{TEXT.failed}</p>
          <p className="text-sm text-muted-foreground">{MESSAGES.common.apiFailures[view.cause]}</p>
          <Button onClick={retry}>{MESSAGES.common.retry}</Button>
        </div>
      )}
    </Card>
  )
}

/**
 * The period the screen opens: the first one that covers today, even a draft. If none does,
 * the first of the list (FEAT-004, decision 8).
 */
function opening(periods: BudgetPeriod[]): BudgetPeriod | undefined {
  return periods.find((candidate) => candidate.is_current) ?? periods[0]
}

function periodLabel(period: BudgetPeriod): string {
  const parts = [
    period.family_group_name ?? TEXT.personal,
    TEXT.periodRange(formatDate(period.period_start), formatDate(period.period_end)),
  ]
  if (period.status === 'draft') parts.push(TEXT.draft)
  return parts.join(TEXT.separator)
}

/**
 * The `budget-…` class names have no style of their own: the tests of this screen find a row,
 * its parts and the state of a bar by them. Do not remove them as unused.
 */
function Summary({ summary, onOpen }: { summary: PeriodSummary; onOpen: (budgetId: string) => void }) {
  const currency = summary.primary_currency
  const noCategories = summary.categories.length === 0
  // With nothing at all the amounts would all be zero, so they are left out. An estimated
  // income loaded without limits is shown, though: hiding it would hide what the user wrote.
  const showAmounts = !noCategories || summary.actual_income !== 0 || summary.estimated_income !== 0
  return (
    <div className="flex flex-col gap-6">
      {showAmounts && (
        <dl className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Figure label={TEXT.estimatedIncome} value={formatAmount(summary.estimated_income, currency)} />
          <Figure label={TEXT.actualIncome} value={formatAmount(summary.actual_income, currency)} />
          <Figure label={TEXT.totalSpent} value={formatAmount(summary.total_spent, currency)} />
        </dl>
      )}
      {noCategories ? (
        // No limits and no spending yet: empty, not a failure.
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">{TEXT.emptyPeriod}</p>
          <CardDescription>{TEXT.emptyPeriodDetail}</CardDescription>
        </div>
      ) : (
        <ul aria-label={TEXT.categories} className="divide-y rounded-lg border">
          {summary.categories.map((category, index) => (
            // Two categories of different members can share a name, so the name is no key.
            <CategoryRow key={category.budget_id ?? index} category={category} currency={currency} onOpen={onOpen} />
          ))}
        </ul>
      )}
    </div>
  )
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-semibold tabular-nums">{value}</dd>
    </div>
  )
}

function CategoryRow({
  category,
  currency,
  onOpen,
}: {
  category: CategorySpending
  currency: string
  onOpen: (budgetId: string) => void
}) {
  const budgetId = category.budget_id
  return (
    <li className="budget-category flex flex-col gap-2 px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {budgetId ? (
          <button
            type="button"
            onClick={() => onOpen(budgetId)}
            className="budget-category__name rounded-sm font-medium underline-offset-4 outline-none hover:underline focus-visible:ring-(length:--focus-ring-width) focus-visible:ring-ring"
          >
            {category.category}
          </button>
        ) : (
          <span className="budget-category__name font-medium">{category.category}</span>
        )}
        <Spending
          spent={category.spent_amount}
          limit={category.limit_amount}
          percentage={category.used_percentage}
          currency={currency}
        />
      </div>
      {category.used_percentage !== null && <Bar label={category.category} percentage={category.used_percentage} />}
    </li>
  )
}

/** What a category spent, and of what limit with which percentage when it has one. */
function Spending({
  spent,
  limit,
  percentage,
  currency,
}: {
  spent: number
  limit: number | null
  percentage: number | null
  currency: string
}) {
  const spentText = formatAmount(spent, currency)
  const state = percentage === null ? null : barState(percentage)
  return (
    <>
      <span className={cn('budget-category__spent ml-auto tabular-nums', spent < 0 && 'text-destructive')}>
        {limit === null ? spentText : TEXT.spentOf(spentText, formatAmount(limit, currency))}
      </span>
      {limit === null && <span className="budget-category__no-limit text-xs text-muted-foreground">{TEXT.noLimit}</span>}
      {percentage !== null && (
        <span className="budget-category__percentage font-semibold tabular-nums">{formatPercentage(percentage)}</span>
      )}
      {state === 'near' && <span className="text-xs font-semibold">{TEXT.nearLimit}</span>}
      {state === 'over' && <span className="text-xs font-semibold text-destructive">{TEXT.overLimit}</span>}
    </>
  )
}

/**
 * Full at 100 % or more, empty when what is spent is negative. It is read aloud as a meter
 * named by its category, with its percentage and state, so the colour is never the only cue.
 */
function Bar({ label, percentage }: { label: string; percentage: number }) {
  const state = barState(percentage)
  const width = Math.min(Math.max(percentage, 0), OVER_LIMIT_PERCENTAGE)
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={OVER_LIMIT_PERCENTAGE}
      aria-valuenow={width}
      aria-valuetext={TEXT.barValue(formatPercentage(percentage), state === 'normal' ? null : TEXT.barStates[state])}
      className={cn('budget-bar h-2 overflow-hidden rounded-full bg-muted', `budget-bar--${state}`)}
    >
      <div
        className={cn(
          'budget-bar__fill h-full rounded-full',
          state === 'normal' && 'bg-primary',
          state === 'near' && 'bg-warning',
          state === 'over' && 'bg-destructive',
        )}
        style={{ width: `${width}%` }}
      />
    </div>
  )
}

/** Past 80 % it is near its limit, and past 100 % it is over it (FEAT-004, decision 9). */
function barState(percentage: number): BarState {
  if (percentage > OVER_LIMIT_PERCENTAGE) return 'over'
  if (percentage > NEAR_LIMIT_PERCENTAGE) return 'near'
  return 'normal'
}

function Detail({ status, onBack }: { status: BudgetStatus; onBack: () => void }) {
  const currency = status.primary_currency
  return (
    <section aria-labelledby="budget-detail-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h3 id="budget-detail-heading" className="font-semibold">
          {status.category}
        </h3>
        <Spending
          spent={status.spent_amount}
          limit={status.limit_amount}
          percentage={status.used_percentage}
          currency={currency}
        />
      </div>
      <Bar label={status.category} percentage={status.used_percentage} />
      <ul aria-label={TEXT.movements} className="divide-y rounded-lg border">
        {status.transactions.map((movement) => (
          <MovementRow key={movement.id} movement={movement} currency={currency} />
        ))}
      </ul>
      <Button variant="outline" className="self-start" onClick={onBack}>
        {TEXT.back}
      </Button>
    </section>
  )
}

/** What it weighs on the limit is shown only when it was converted: otherwise it is its amount. */
function MovementRow({ movement, currency }: { movement: BudgetMovement; currency: string }) {
  return (
    <li className="budget-movement flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-sm">
      <span className="budget-movement__date text-muted-foreground tabular-nums">
        {formatDate(movement.transaction_date)}
      </span>
      {movement.description && <span className="budget-movement__description">{movement.description}</span>}
      <Tag className="budget-movement__type">{TEXT.types[movement.type]}</Tag>
      <span className="budget-movement__amount font-semibold tabular-nums">
        {formatAmount(movement.amount, movement.currency)}
      </span>
      {movement.exchange_rate !== null && (
        <>
          <span className="budget-movement__exchange-rate text-muted-foreground">
            {TEXT.exchangeRate(formatRate(movement.exchange_rate))}
          </span>
          <span className="budget-movement__weight tabular-nums" title={TEXT.weighs}>
            {formatAmount(movement.budget_amount, currency)}
          </span>
        </>
      )}
      <span className="budget-movement__account ml-auto">{movement.account}</span>
      <Tag className="budget-movement__source">{TEXT.sources[movement.source]}</Tag>
    </li>
  )
}

function Tag({ className, children }: { className: string; children: string }) {
  return (
    <span className={cn(className, 'rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground')}>{children}</span>
  )
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

/** The percentage as the API rounded it, with its one decimal. */
function formatPercentage(percentage: number): string {
  return TEXT.percentage(
    new Intl.NumberFormat(AMOUNT_LOCALE, {
      minimumFractionDigits: PERCENTAGE_DECIMALS,
      maximumFractionDigits: PERCENTAGE_DECIMALS,
    }).format(percentage),
  )
}

function formatRate(rate: number): string {
  return new Intl.NumberFormat(AMOUNT_LOCALE, { maximumFractionDigits: EXCHANGE_RATE_MAX_DECIMALS }).format(rate)
}

/**
 * An ISO date, as 2026-10-09, written as 9/10/2026. It is a calendar day: it is read and
 * written in UTC, so no time zone moves it to the day before.
 */
function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat(DATE_LOCALE, { ...DATE_FORMAT, timeZone: DATE_TIME_ZONE }).format(
    new Date(isoDate),
  )
}
