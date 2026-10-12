import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { API_ROUTES } from './src/api/routes.ts'

// The address of the API while developing. In every deployed environment the dashboard and
// the API share one origin (ADR 0016), so the code only ever uses relative paths.
const DEV_API = 'http://127.0.0.1:8000'

export default defineConfig({
  // The API serves the build under /app (ADR 0016).
  base: '/app/',
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
