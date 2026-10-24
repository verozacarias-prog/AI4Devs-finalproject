import { defineConfig, devices } from '@playwright/test'

/**
 * The end-to-end test (#79): a real browser against the whole application, started with
 * Docker Compose. `npm run test:e2e` runs it. The API of that stack listens on its own port,
 * so it never touches the one of `docker compose up`.
 */
export default defineConfig({
  testDir: './e2e',
  // Starts the stack from an empty database, and removes it after the run.
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
  // The test changes a balance: one run at a time, against one database.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    // The session cookie is Secure, and Chromium keeps it over http on localhost (ADR 0016).
    baseURL: 'http://localhost:8001/app/',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
