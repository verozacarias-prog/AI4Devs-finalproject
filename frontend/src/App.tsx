import { Activity, LogOut, Wallet } from 'lucide-react'
import { useCallback, useState, type ReactNode } from 'react'
import type { Failure } from './api/request'
import { logout } from './api/session'
import type { SessionUser } from './api/session'
import { cn } from './lib/utils'
import { MESSAGES } from './messages'
import { AccountsPage } from './pages/AccountsPage'
import { DevEntryPage } from './pages/DevEntryPage'
import { StatusPage } from './pages/StatusPage'

/** The screens of the menu. The menu is a state of the page, without a router (ADR 0027). */
type Screen = 'accounts' | 'status'

type LogoutFailure = Exclude<Failure['kind'], 'cancelled'>

const NAV = MESSAGES.nav

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [screen, setScreen] = useState<Screen>('accounts')
  // Why closing the session failed: the session is still alive, so the menu stays.
  const [logoutFailure, setLogoutFailure] = useState<LogoutFailure | null>(null)
  // Changing it starts the entry again, to show it when the session ended.
  const [entry, setEntry] = useState(0)
  const sessionEnded = useCallback(() => {
    setUser(null)
    setScreen('accounts')
    setLogoutFailure(null)
    setEntry((current) => current + 1)
  }, [])

  function closeSession() {
    setLogoutFailure(null)
    void logout().then((closed) => {
      if (closed.kind === 'closed') sessionEnded()
      else if (closed.kind !== 'cancelled') setLogoutFailure(closed.kind)
    })
  }

  if (user === null) {
    // Without a session there is no menu: only the way in, and whether the system is up.
    return (
      <main className="mx-auto flex max-w-xl flex-col gap-6 px-4 py-10">
        <Brand />
        <DevEntryPage key={entry} onSessionChange={setUser} />
        <StatusPage />
      </main>
    )
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[var(--sidebar-width)_1fr]">
      <aside className="flex flex-col gap-4 bg-sidebar px-4 py-4 text-sidebar-foreground md:min-h-screen md:py-6">
        <Brand inverted />
        <nav aria-label={NAV.label} className="flex flex-wrap gap-1 md:flex-col md:gap-4">
          <ul className="flex gap-1 md:flex-col">
            <NavItem current={screen === 'accounts'} onSelect={() => setScreen('accounts')} icon={<Wallet />}>
              {NAV.accounts}
            </NavItem>
          </ul>
          <div className="flex items-center gap-1 md:flex-col md:items-stretch">
            <p id="nav-testing" className="px-3 text-xs font-semibold tracking-wide text-sidebar-muted uppercase">
              {NAV.testing}
            </p>
            <ul aria-labelledby="nav-testing" className="flex gap-1 md:flex-col">
              <NavItem current={screen === 'status'} onSelect={() => setScreen('status')} icon={<Activity />}>
                {NAV.status}
              </NavItem>
            </ul>
          </div>
        </nav>
        <div className="flex items-center justify-between gap-2 border-t border-sidebar-accent pt-4 md:mt-auto md:flex-col md:items-stretch">
          <p className="px-3 text-sm">
            <span className="block text-xs text-sidebar-muted">{NAV.signedInAs}</span>
            <span className="font-semibold">{user.name}</span>
          </p>
          <button
            type="button"
            onClick={closeSession}
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-muted transition-colors outline-none hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:ring-(length:--focus-ring-width) focus-visible:ring-sidebar-primary/60 [&_svg]:size-4"
          >
            <LogOut aria-hidden="true" />
            {NAV.logout}
          </button>
          {logoutFailure && (
            <div role="alert" className="px-3 text-sm">
              <p className="font-semibold text-sidebar-destructive">{NAV.logoutFailed}</p>
              <p className="text-sidebar-muted">{MESSAGES.common.apiFailures[logoutFailure]}</p>
            </div>
          )}
        </div>
      </aside>
      <main className="mx-auto w-full max-w-3xl px-4 py-6 md:px-10 md:py-10">
        {screen === 'accounts' ? <AccountsPage key={user.id} onNoSession={sessionEnded} /> : <StatusPage />}
      </main>
    </div>
  )
}

function Brand({ inverted = false }: { inverted?: boolean }) {
  return (
    <div className="px-3">
      <h1 className={cn('text-2xl font-bold tracking-tight', inverted ? 'text-sidebar-primary' : 'text-primary')}>
        {MESSAGES.appTitle}
      </h1>
      <p className={cn('text-sm', inverted ? 'text-sidebar-muted' : 'text-muted-foreground')}>{MESSAGES.appTagline}</p>
    </div>
  )
}

function NavItem({
  current,
  onSelect,
  icon,
  children,
}: {
  current: boolean
  onSelect: () => void
  icon: ReactNode
  children: string
}) {
  return (
    <li>
      <button
        type="button"
        aria-current={current ? 'page' : undefined}
        onClick={onSelect}
        className={cn(
          'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors outline-none focus-visible:ring-(length:--focus-ring-width) focus-visible:ring-sidebar-primary/60 [&_svg]:size-4',
          current
            ? 'bg-sidebar-accent text-sidebar-primary'
            : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground',
        )}
      >
        <span aria-hidden="true">{icon}</span>
        {children}
      </button>
    </li>
  )
}
