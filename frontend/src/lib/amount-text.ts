import {
  AMOUNT_SEPARATORS,
  API_DECIMAL_POINT,
  PERIOD_AMOUNT_NUMBERS,
  THOUSANDS_GROUP_BOUNDARY,
  THOUSANDS_GROUP_SIZE,
  TRAILING_ZEROS,
} from '../constants'

type Separators = typeof AMOUNT_SEPARATORS

/** An amount with the exact digits the API wrote. */
export type AmountDigits = `${number}`

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
export function amountFromApi(amount: AmountDigits, separators: Separators = AMOUNT_SEPARATORS): string {
  const [whole, decimals = ''] = amount.split(API_DECIMAL_POINT)
  const grouped = whole.replace(THOUSANDS_GROUP_BOUNDARY, separators.thousands)
  const kept = decimals.replace(TRAILING_ZEROS, '')
  return kept === '' ? grouped : grouped + separators.decimal + kept
}

/**
 * The text of an answer with the amounts of its periods turned into JSON texts. The API writes
 * them as numbers with their exact digits, and a number of JavaScript cannot hold them all.
 */
export function periodAmountsAsText(answer: string): string {
  return answer.replace(PERIOD_AMOUNT_NUMBERS, '"$1":"$2"')
}

function onlyDigits(text: string): string {
  return [...text].filter((character) => /\d/.test(character)).join('')
}
