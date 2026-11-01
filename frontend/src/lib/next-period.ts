import type { BudgetPeriod } from '../api/budget'
import { ISO_DATE_LENGTH } from '../constants'

/** The individual period that starts latest, even a draft (FEAT-005, CA-13). */
export function lastIndividualPeriod(periods: BudgetPeriod[]): BudgetPeriod | null {
  const individual = periods.filter((candidate) => candidate.family_group_id === null)
  if (individual.length === 0) return null
  return individual.reduce((latest, candidate) => (candidate.period_start > latest.period_start ? candidate : latest))
}

/** The first free day after that period, as an ISO date: where the next one can start. */
export function nextPeriodStart(last: BudgetPeriod): string {
  const day = new Date(last.period_end)
  day.setUTCDate(day.getUTCDate() + 1)
  return day.toISOString().slice(0, ISO_DATE_LENGTH)
}
