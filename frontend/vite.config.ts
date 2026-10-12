import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { API_ROUTES } from './src/api/routes.ts'
import { DASHBOARD_BASE } from './src/constants.ts'

// The address of the API while developing. In every deployed environment the dashboard and
// the API share one origin (ADR 0016), so the code only ever uses relative paths.
const DEV_API = 'http://127.0.0.1:8000'

export default defineConfig({
  base: DASHBOARD_BASE,
  plugins: [react()],
  server: {
    // Every API path goes to the API; the rest is the dashboard.
    proxy: Object.fromEntries(Object.values(API_ROUTES).map((path) => [path, DEV_API])),
  },
  test: {
    environment: 'jsdom',
    restoreMocks: true,
  },
})
