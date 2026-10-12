import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { API_ROUTES } from './src/api/routes.ts'
import { DASHBOARD_BASE, DEV_API_ORIGIN } from './src/constants.ts'

export default defineConfig({
  base: DASHBOARD_BASE,
  plugins: [react()],
  server: {
    // Every API path goes to the API; the rest is the dashboard.
    proxy: Object.fromEntries(Object.values(API_ROUTES).map((path) => [path, DEV_API_ORIGIN])),
  },
  test: {
    environment: 'jsdom',
    restoreMocks: true,
  },
})
