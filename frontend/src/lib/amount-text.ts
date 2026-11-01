import { AMOUNT_SEPARATORS, API_DECIMAL_POINT, THOUSANDS_GROUP_BOUNDARY, THOUSANDS_GROUP_SIZE } from '../constants'

type Separators = typeof AMOUNT_SEPARATORS

/** What an amount field keeps of what is typed: digits, thousands separators and one decimal separator. */
export function amountText(written: string, separators: Separators = AMOUNT_SEPARATORS): string {
  const [whole, ...decimals] = written.split(separators.decimal)
  const kept = [...whole].filter((character) => /\d/.test(character) || character === separators.thousands).join('')
  if (decimals.length === 0) return kept
  return kept + separators.decimal + onlyDigits(decimals.join(''))
}

/** Whether each thousands separator really separates thousands: 1.5 could mean 1,5 or 15. */
export function thousandsAreWellPlaced(written: string, separators: Separators = AMOUNT_SEPARATORS): boolean {
  const [whole] = written.trim().split(separators.decimal)
  const [first, ...groups] = whole.split(separators.thousands)
  return groups.length === 0 || (first !== '' && groups.every((group) => group.length === THOUSANDS_GROUP_SIZE))
}

/** An amount as the person wrote it, in the plain decimal text the API takes. */
export function amountForApi(written: string, separators: Separators = AMOUNT_SEPARATORS): string {
  const [whole, decimals] = written.trim().split(separators.decimal)
  const digits = onlyDigits(whole)
  return decimals === undefined ? digits : digits + API_DECIMAL_POINT + decimals
}

/** An amount that came from the API, the way a person writes it. */
export function amountFromApi(amount: number, separators: Separators = AMOUNT_SEPARATORS): string {
  const [whole, decimals] = String(amount).split(API_DECIMAL_POINT)
  const grouped = whole.replace(THOUSANDS_GROUP_BOUNDARY, separators.thousands)
  return decimals === undefined ? grouped : grouped + separators.decimal + decimals
}

function onlyDigits(text: string): string {
  return [...text].filter((character) => /\d/.test(character)).join('')
}
