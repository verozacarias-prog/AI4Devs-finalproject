import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { formatAmount, formatDate } from '@/lib/budget-format'
import {
  confirmPeriod,
  loadBudgetPeriods,
  loadCategories,
  savePeriod,
  type BudgetPeriod,
  type Category,
  type Loaded,
  type PeriodContent,
  type Saved,
} from '../api/budget'
import type { Failure } from '../api/request'
import { API_ERROR_NOT_FOUND, ISO_DATE_LENGTH } from '../constants'
import { MESSAGES } from '../messages'

/**
 * Builds a budget period, or changes one, and confirms it (FEAT-005). The screen does no sums:
 * each amount travels as the text the user wrote, and the API decides what is valid. What it
 * decides by itself is what a new period starts with: a copy of the last one (CA-13).
 */
type ErrorCause = Exclude<Failure['kind'], 'cancelled'>

type Limit = { key: string; categoryId: string; amount: string }

type Fields = {
  periodType: BudgetPeriod['period_type']
  start: string
  end: string
  currency: string
  income: string
  limits: Limit[]
}

type View = { kind: 'loading' } | { kind: 'editing' } | { kind: 'saved' } | { kind: 'confirmed' }

/** Why a request failed: what can be repeated as it was, or what the API refused. */
type Problem =
  | { kind: 'load'; cause: ErrorCause }
  | { kind: 'save'; cause: ErrorCause }
  | { kind: 'confirm'; cause: ErrorCause }
  | { kind: 'refused'; code: string }

const TEXT = MESSAGES.budgetForm
const CONTROL =
  'rounded-md border bg-card px-3 py-2 outline-none focus-visible:ring-(length:--focus-ring-width) focus-visible:ring-ring disabled:opacity-60'

const EMPTY_FIELDS: Fields = { periodType: 'monthly', start: '', end: '', currency: '', income: '', limits: [] }

type Props = {
  /** The period to change, or null to build a new one. */
  periodId: string | null
  /** Back to the summary, with the period to show if one was saved. */
  onDone: (periodId: string | null) => void
  /** Called when the API says there is no session: the entry is shown again. */
  onNoSession: () => void
  /** How long to wait for the API. Tests pass a short one. */
  timeoutMs?: number
}

export function BudgetPeriodFormPage({ periodId, onDone, onNoSession, timeoutMs }: Props) {
  const [categories, setCategories] = useState<Category[] | null>(null)
  const [periods, setPeriods] = useState<BudgetPeriod[] | null>(null)
  const [period, setPeriod] = useState<BudgetPeriod | null>(null)
  const [fields, setFields] = useState<Fields>(EMPTY_FIELDS)
  const [view, setView] = useState<View>({ kind: 'loading' })
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<Problem | null>(null)
  // Retrying the first load repeats only the query that failed.
  const [attempt, setAttempt] = useState(0)
  const statusLine = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    const stop = new AbortController()
    const options = { timeoutMs, signal: stop.signal }
    void Promise.all([
      categories ? already(categories) : loadCategories(options),
      periods ? already(periods) : loadBudgetPeriods(options),
    ]).then(([categoriesLoaded, periodsLoaded]) => {
      if (stop.signal.aborted || categoriesLoaded.kind === 'cancelled' || periodsLoaded.kind === 'cancelled') return
      if (categoriesLoaded.kind === 'no-session' || periodsLoaded.kind === 'no-session') return onNoSession()
      if (categoriesLoaded.kind === 'loaded') setCategories(categoriesLoaded.value)
      if (periodsLoaded.kind === 'loaded') setPeriods(periodsLoaded.value)
      if (categoriesLoaded.kind !== 'loaded') return setProblem({ kind: 'load', cause: categoriesLoaded.kind })
      if (periodsLoaded.kind !== 'loaded') return setProblem({ kind: 'load', cause: periodsLoaded.kind })
      const stored = periodsLoaded.value.find((candidate) => candidate.id === periodId) ?? null
      if (periodId !== null && stored === null) return setProblem({ kind: 'refused', code: API_ERROR_NOT_FOUND })
      setPeriod(stored)
      setFields(stored ? fieldsOf(stored) : copyOfLast(periodsLoaded.value))
      setProblem(null)
      setView({ kind: 'editing' })
    })
    return () => stop.abort()
    // The lists are read only to skip what already arrived: they do not start a new load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, periodId, timeoutMs, onNoSession])

  function settle(saved: Saved, next: View, failedKind: 'save' | 'confirm') {
    setBusy(false)
    if (saved.kind === 'cancelled') return
    if (saved.kind === 'no-session') return onNoSession()
    if (saved.kind === 'refused') return setProblem({ kind: 'refused', code: saved.code })
    if (saved.kind !== 'saved') return setProblem({ kind: failedKind, cause: saved.kind })
    setPeriod(saved.value)
    setFields(fieldsOf(saved.value))
    setView(next)
  }

  function send() {
    setBusy(true)
    setProblem(null)
    void savePeriod(contentOf(fields), period?.id ?? null, { timeoutMs }).then((saved) =>
      settle(saved, { kind: 'saved' }, 'save'),
    )
  }

  function confirm() {
    if (period === null) return
    setBusy(true)
    setProblem(null)
    void confirmPeriod(period.id, { timeoutMs }).then((saved) => settle(saved, { kind: 'confirmed' }, 'confirm'))
  }

  function retry() {
    const failed = problem
    setProblem(null)
    statusLine.current?.focus()
    if (failed?.kind === 'save') send()
    else if (failed?.kind === 'confirm') confirm()
    else setAttempt((current) => current + 1)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    send()
  }

  const fixed = period?.status === 'confirmed'
  const options = categoryOptions(categories ?? [], period)

  return (
    <Card aria-labelledby="period-form-heading">
      <CardTitle id="period-form-heading" className="text-xl">
        {period ? TEXT.headingEdit : TEXT.headingNew}
      </CardTitle>
      <p ref={statusLine} role="status" tabIndex={-1} className="text-sm text-muted-foreground outline-none empty:hidden">
        {statusText(view, busy, problem)}
      </p>
      {view.kind === 'editing' && (
        <form onSubmit={submit} className="flex flex-col gap-4">
          <fieldset disabled={busy} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm font-medium">
                {TEXT.cadence}
                <select
                  value={fields.periodType}
                  disabled={fixed}
                  onChange={(event) =>
                    setFields({ ...fields, periodType: event.target.value as Fields['periodType'] })
                  }
                  className={CONTROL}
                >
                  <option value="monthly">{TEXT.cadences.monthly}</option>
                  <option value="biweekly">{TEXT.cadences.biweekly}</option>
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm font-medium">
                {TEXT.currency}
                <input
                  value={fields.currency}
                  required
                  disabled={fixed}
                  onChange={(event) => setFields({ ...fields, currency: event.target.value.toUpperCase() })}
                  className={CONTROL}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm font-medium">
                {TEXT.start}
                <input
                  type="date"
                  value={fields.start}
                  required
                  disabled={fixed}
                  onChange={(event) => setFields({ ...fields, start: event.target.value })}
                  className={CONTROL}
                />
              </label>
              <div className="flex flex-col gap-1">
                <label className="flex flex-col gap-1 text-sm font-medium">
                  {TEXT.end}
                  <input
                    type="date"
                    value={fields.end}
                    disabled={fixed}
                    aria-describedby="period-end-hint"
                    onChange={(event) => setFields({ ...fields, end: event.target.value })}
                    className={CONTROL}
                  />
                </label>
                {fields.periodType === 'monthly' && !fixed && (
                  <span id="period-end-hint" className="text-xs text-muted-foreground">
                    {TEXT.endHint}
                  </span>
                )}
              </div>
              <label className="flex flex-col gap-1 text-sm font-medium">
                {TEXT.income}
                <input
                  inputMode="decimal"
                  value={fields.income}
                  required
                  onChange={(event) => setFields({ ...fields, income: event.target.value })}
                  className={CONTROL}
                />
              </label>
            </div>
            <Limits
              limits={fields.limits}
              options={options}
              onChange={(limits) => setFields({ ...fields, limits })}
            />
          </fieldset>
          {problem && <ProblemAlert problem={problem} onRetry={retry} />}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={busy}>
              {TEXT.save}
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={() => onDone(period?.id ?? null)}>
              {TEXT.back}
            </Button>
          </div>
        </form>
      )}
      {view.kind === 'saved' && period && (
        <section className="flex flex-col gap-4">
          <p className="text-sm font-medium">{TEXT.savedNotice}</p>
          <PeriodContentList period={period} />
          {problem && <ProblemAlert problem={problem} onRetry={retry} />}
          <div className="flex flex-wrap gap-2">
            {period.status === 'draft' && (
              <Button disabled={busy} onClick={confirm}>
                {TEXT.confirm}
              </Button>
            )}
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => {
                setProblem(null)
                setView({ kind: 'editing' })
              }}
            >
              {TEXT.edit}
            </Button>
            <Button variant="outline" disabled={busy} onClick={() => onDone(period.id)}>
              {TEXT.back}
            </Button>
          </div>
        </section>
      )}
      {view.kind === 'confirmed' && period && (
        <section className="flex flex-col gap-4">
          <p className="text-sm font-medium">{TEXT.confirmedNotice(formatDate(period.period_start))}</p>
          <PeriodContentList period={period} />
          <Button className="self-start" onClick={() => onDone(period.id)}>
            {TEXT.back}
          </Button>
        </section>
      )}
      {view.kind === 'loading' && problem && <ProblemAlert problem={problem} onRetry={retry} onBack={() => onDone(null)} />}
    </Card>
  )
}

function Limits({
  limits,
  options,
  onChange,
}: {
  limits: Limit[]
  options: { id: string; name: string }[]
  onChange: (limits: Limit[]) => void
}) {
  if (options.length === 0) {
    // The query worked and there is nothing to choose: empty, not a failure.
    return (
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">{TEXT.noCategories}</p>
        <CardDescription>{TEXT.noCategoriesDetail}</CardDescription>
      </div>
    )
  }
  const change = (key: string, changes: Partial<Limit>) =>
    onChange(limits.map((limit) => (limit.key === key ? { ...limit, ...changes } : limit)))
  const add = () => {
    const taken = new Set(limits.map((limit) => limit.categoryId))
    const free = options.find((option) => !taken.has(option.id)) ?? options[0]
    onChange([...limits, { key: crypto.randomUUID(), categoryId: free.id, amount: '' }])
  }
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-sm font-medium">{TEXT.limits}</legend>
      {limits.map((limit, index) => (
        <div key={limit.key} className="flex flex-wrap items-end gap-2">
          <label className="flex grow flex-col gap-1 text-sm">
            {TEXT.limitCategory(index + 1)}
            <select
              value={limit.categoryId}
              onChange={(event) => change(limit.key, { categoryId: event.target.value })}
              className={CONTROL}
            >
              {options.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            {TEXT.limitAmount(index + 1)}
            <input
              inputMode="decimal"
              value={limit.amount}
              required
              onChange={(event) => change(limit.key, { amount: event.target.value })}
              className={CONTROL}
            />
          </label>
          <Button
            type="button"
            variant="outline"
            aria-label={TEXT.removeLimitLabel(index + 1)}
            onClick={() => onChange(limits.filter((candidate) => candidate.key !== limit.key))}
          >
            {TEXT.removeLimit}
          </Button>
        </div>
      ))}
      <Button type="button" variant="outline" className="self-start" onClick={add}>
        {TEXT.addLimit}
      </Button>
    </fieldset>
  )
}

function PeriodContentList({ period }: { period: BudgetPeriod }) {
  const currency = period.primary_currency
  return (
    <dl className="flex flex-col gap-2 text-sm">
      <Row label={TEXT.cadence} value={TEXT.cadences[period.period_type]} />
      <Row label={TEXT.dates} value={MESSAGES.budget.periodRange(formatDate(period.period_start), formatDate(period.period_end))} />
      <Row label={TEXT.income} value={formatAmount(period.estimated_income, currency)} />
      {period.budgets.map((budget) => (
        <Row key={budget.id} label={budget.category} value={formatAmount(budget.limit_amount, currency)} />
      ))}
    </dl>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap justify-between gap-x-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  )
}

function ProblemAlert({ problem, onRetry, onBack }: { problem: Problem; onRetry: () => void; onBack?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-2">
      {problem.kind === 'refused' ? (
        <p className="font-semibold text-destructive">{refusalText(problem.code)}</p>
      ) : (
        <>
          <p className="font-semibold text-destructive">{problem.kind === 'load' ? TEXT.loadFailed : TEXT.saveFailed}</p>
          <p className="text-sm text-muted-foreground">{MESSAGES.common.apiFailures[problem.cause]}</p>
          <Button type="button" onClick={onRetry}>
            {MESSAGES.common.retry}
          </Button>
        </>
      )}
      {onBack && (
        <Button type="button" variant="outline" onClick={onBack}>
          {TEXT.back}
        </Button>
      )}
    </div>
  )
}

function statusText(view: View, busy: boolean, problem: Problem | null): string {
  if (busy) return TEXT.saving
  return view.kind === 'loading' && problem === null ? TEXT.loading : ''
}

/** A list that arrived in an earlier attempt, so that a retry does not ask for it again. */
function already<T>(value: T): Loaded<T> {
  return { kind: 'loaded', value }
}

function refusalText(code: string): string {
  const known: Record<string, string> = TEXT.refusals
  return known[code] ?? MESSAGES.common.apiFailures['api-error']
}

/** The categories to choose from, and those the period already has, whoever they belong to. */
function categoryOptions(categories: Category[], period: BudgetPeriod | null): { id: string; name: string }[] {
  const known = new Set(categories.map((category) => category.id))
  const others = (period?.budgets ?? [])
    .filter((budget) => !known.has(budget.category_id))
    .map((budget) => ({ id: budget.category_id, name: budget.category }))
  return [...categories.map((category) => ({ id: category.id, name: category.name })), ...others]
}

function fieldsOf(period: BudgetPeriod): Fields {
  return {
    periodType: period.period_type,
    start: period.period_start,
    end: period.period_end,
    currency: period.primary_currency,
    income: String(period.estimated_income),
    limits: limitsOf(period),
  }
}

function limitsOf(period: BudgetPeriod): Limit[] {
  return period.budgets.map((budget) => ({
    key: budget.id,
    categoryId: budget.category_id,
    amount: String(budget.limit_amount),
  }))
}

/**
 * A new period starts as a copy of the last individual one, the one that starts latest even if
 * it is a draft, from the day after it ends, with its end empty (CA-13).
 */
function copyOfLast(periods: BudgetPeriod[]): Fields {
  const individual = periods.filter((candidate) => candidate.family_group_id === null)
  if (individual.length === 0) return EMPTY_FIELDS
  const last = individual.reduce((latest, candidate) =>
    candidate.period_start > latest.period_start ? candidate : latest,
  )
  return { ...fieldsOf(last), start: dayAfter(last.period_end), end: '' }
}

function dayAfter(isoDate: string): string {
  const day = new Date(isoDate)
  day.setUTCDate(day.getUTCDate() + 1)
  return day.toISOString().slice(0, ISO_DATE_LENGTH)
}

/** Each amount goes as the text the user wrote, with the decimal comma they may have used. */
function contentOf(fields: Fields): PeriodContent {
  return {
    period_type: fields.periodType,
    period_start: fields.start,
    period_end: fields.end === '' ? null : fields.end,
    primary_currency: fields.currency.trim(),
    estimated_income: decimalText(fields.income),
    budgets: fields.limits.map((limit) => ({
      category_id: limit.categoryId,
      limit_amount: decimalText(limit.amount),
    })),
  }
}

function decimalText(amount: string): string {
  return amount.trim().replace(',', '.')
}
