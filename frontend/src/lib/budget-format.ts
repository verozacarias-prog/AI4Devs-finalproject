import { AMOUNT_DECIMALS, AMOUNT_LOCALE, DATE_FORMAT, DATE_LOCALE, DATE_TIME_ZONE } from '../constants'

/** Writes an amount with its currency, so it is never read as a bare number. */
export function formatAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat(AMOUNT_LOCALE, {
    style: 'currency',
    currency,
    minimumFractionDigits: AMOUNT_DECIMALS,
    maximumFractionDigits: AMOUNT_DECIMALS,
  }).format(amount)
}

/**
 * An ISO date, as 2026-10-09, written as 9/10/2026. It is a calendar day: it is read and
 * written in UTC, so no time zone moves it to the day before.
 */
export function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat(DATE_LOCALE, { ...DATE_FORMAT, timeZone: DATE_TIME_ZONE }).format(
    new Date(isoDate),
  )
}
