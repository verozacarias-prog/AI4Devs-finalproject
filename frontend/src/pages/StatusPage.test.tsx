/**
 * Cases 35 to 39: the states of the status page. The API is simulated at the network level,
 * so the page and its API call are tested together.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test } from 'vitest'
import { StatusPage } from './StatusPage'

const READYZ = '*/readyz'
const ready = () => HttpResponse.json({ status: 'ok' })
const databaseDown = () => HttpResponse.json({ status: 'unavailable' }, { status: 503 })
const apiDown = () => HttpResponse.error()

const api = setupServer()

beforeAll(() => api.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  cleanup()
  api.resetHandlers()
})
afterAll(() => api.close())

test('case 35: while the API is being asked, it says so', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(READYZ, async () => {
      await pending
      return ready()
    }),
  )

  render(<StatusPage />)

  expect(screen.getByRole('status').textContent).toBe('Consultando el estado…')
  answer()
  await screen.findByText('Todo conectado')
})

test('case 36: when the API reaches the database, everything is connected', async () => {
  api.use(http.get(READYZ, ready))

  render(<StatusPage />)

  await screen.findByText('Todo conectado')
  expect(screen.getByRole('status').textContent).toBe('Todo conectado')
  screen.getByText('El dashboard llega a la API, y la API a la base de datos.')
  expect(screen.queryByRole('alert')).toBeNull()
})

test('case 37: when the API cannot reach the database, it is an error with a retry', async () => {
  api.use(http.get(READYZ, databaseDown))

  render(<StatusPage />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Sin conexión')
  expect(alert.textContent).toContain('La API responde, pero no llega a la base de datos.')
  screen.getByRole('button', { name: 'Reintentar' })
})

test('case 38: when the API cannot be reached, it is an error with a retry', async () => {
  api.use(http.get(READYZ, apiDown))

  render(<StatusPage />)

  const alert = await screen.findByRole('alert')
  expect(alert.textContent).toContain('Sin conexión')
  expect(alert.textContent).toContain('No se puede llegar a la API.')
  screen.getByRole('button', { name: 'Reintentar' })
})

test('case 39: retrying after an error asks again and ends connected', async () => {
  let answer: () => void = () => {}
  const pending = new Promise<void>((resolve) => {
    answer = resolve
  })
  api.use(
    http.get(READYZ, async () => {
      await pending
      return ready()
    }),
  )
  // The handler added last runs first: the first request fails, the second one waits.
  api.use(http.get(READYZ, apiDown, { once: true }))

  render(<StatusPage />)
  const retry = await screen.findByRole('button', { name: 'Reintentar' })
  retry.click()

  expect((await screen.findByRole('status')).textContent).toBe('Consultando el estado…')
  expect(screen.queryByRole('alert')).toBeNull()
  answer()
  await screen.findByText('Todo conectado')
})
