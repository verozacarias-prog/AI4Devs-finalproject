import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

/**
 * Starts and removes the end-to-end stack (#79): Docker Compose with compose.e2e.yml on top,
 * under a project name of its own. Each run starts from an empty database with the test users
 * loaded, and ends removing it.
 */
const ROOT = fileURLToPath(new URL('../..', import.meta.url))
const COMPOSE = [
  'compose',
  '--project-name',
  'platita-e2e',
  '--env-file',
  'frontend/e2e/compose.env',
  '--file',
  'docker-compose.yml',
  '--file',
  'frontend/e2e/compose.e2e.yml',
]
const SEED_TEST_DATA = ['python', '-m', 'app.adapters.inbound.operator_commands.seed_test_data']

function docker(...args: string[]): void {
  execFileSync('docker', [...COMPOSE, ...args], { cwd: ROOT, stdio: 'inherit' })
}

export function startStack(): void {
  // A stack left by a run that did not finish would keep its balances.
  docker('down', '--volumes', '--remove-orphans')
  docker('up', '--detach', '--build', '--wait')
  docker('exec', '-T', 'api', ...SEED_TEST_DATA)
}

export function removeStack(): void {
  docker('down', '--volumes', '--remove-orphans')
}
