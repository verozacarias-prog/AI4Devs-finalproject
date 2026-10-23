import { expect, test, type Locator, type Page } from '@playwright/test'

/**
 * E2E-1 (#79): the main flow, end to end. Lucía writes an expense in the chat, the worker
 * answers it through the real adapter of the model, pointed at a fake provider, and the
 * accounts screen shows the new balance. Every piece runs as it does locally, from a fresh
 * database with the test users loaded.
 */
test('an expense written in the chat lowers the balance of its account', async ({ page }) => {
  await page.goto('')
  await page.getByRole('button', { name: 'Entrar como Lucía' }).click()

  await expect(amountOf(page, 'Mercado Pago')).toHaveText(/^\$\s80\.000,00$/)
  const othersBefore = await otherAmounts(page)
  expect(Object.keys(othersBefore).sort()).toEqual(['Efectivo', 'Galicia USD', 'Galicia pesos'])

  await page.getByRole('button', { name: 'Chat' }).click()
  await page.getByLabel('Tu mensaje').fill('gasté 1500 en el súper con Mercado Pago')
  await page.getByRole('button', { name: 'Enviar' }).click()
  await expect(page.getByRole('log')).toContainText('¡Listo! Anoté un gasto de $1.500 en Mercado Pago.')

  await page.getByRole('button', { name: 'Cuentas' }).click()
  await expect(amountOf(page, 'Mercado Pago')).toHaveText(/^\$\s78\.500,00$/)
  expect(await otherAmounts(page)).toEqual(othersBefore)
})

function accountRow(page: Page, name: string): Locator {
  return page.locator('.account').filter({ has: page.locator('.account__name', { hasText: new RegExp(`^${name}$`) }) })
}

function amountOf(page: Page, name: string): Locator {
  return accountRow(page, name).locator('.account__amount')
}

/** Every account but Mercado Pago, by name, with the amount the screen shows. */
async function otherAmounts(page: Page): Promise<Record<string, string>> {
  const amounts: Record<string, string> = {}
  for (const row of await page.locator('.account').all()) {
    const name = await row.locator('.account__name').innerText()
    if (name !== 'Mercado Pago') amounts[name] = await row.locator('.account__amount').innerText()
  }
  return amounts
}
