import { execFileSync } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'
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
// The API answers 200 here once it reaches the database (docs/04-api.md).
const READY_URL = 'http://localhost:8001/readyz'
const LONGEST_START_MS = 120_000
const POLL_MS = 1_000

function docker(...args: string[]): void {
  execFileSync('docker', [...COMPOSE, ...args], { cwd: ROOT, stdio: 'inherit' })
}

function runningServices(): string[] {
  const output = execFileSync('docker', [...COMPOSE, 'ps', '--status', 'running', '--services'], {
    cwd: ROOT,
    encoding: 'utf8',
  })
  return output.split('\n').filter(Boolean)
}

async function apiReady(): Promise<boolean> {
  try {
    return (await fetch(READY_URL)).ok
  } catch {
    return false
  }
}

export async function startStack(): Promise<void> {
  // A stack left by a run that did not finish would keep its balances.
  docker('down', '--volumes', '--remove-orphans')
  // Not --wait: some versions of Compose take the migrations, which finish and exit, for a
  // failure. The API and the worker already wait for them; this waits for those two.
  docker('up', '--detach', '--build')
  const deadline = Date.now() + LONGEST_START_MS
  while (!((await apiReady()) && runningServices().includes('worker'))) {
    if (Date.now() > deadline) throw new Error('The end-to-end stack did not start in time')
    await sleep(POLL_MS)
  }
  docker('exec', '-T', 'api', ...SEED_TEST_DATA)
}

export function removeStack(): void {
  // CI keeps it, to read the logs of the containers when the test failed.
  if (process.env.E2E_KEEP_STACK === 'true') return
  docker('down', '--volumes', '--remove-orphans')
}
