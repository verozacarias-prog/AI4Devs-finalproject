import { useCallback, useState } from 'react'
import { logout } from './api/session'
import type { SessionUser } from './api/session'
import { AppShell, type LogoutFailure, type Screen } from './components/AppShell'
import { Brand } from './components/Brand'
import { AccountsPage } from './pages/AccountsPage'
import { DevEntryPage } from './pages/DevEntryPage'
import { StatusPage } from './pages/StatusPage'

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [screen, setScreen] = useState<Screen>('accounts')
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
    <AppShell user={user} screen={screen} onSelect={setScreen} onLogout={closeSession} logoutFailure={logoutFailure}>
      {screen === 'accounts' ? <AccountsPage key={user.id} onNoSession={sessionEnded} /> : <StatusPage />}
    </AppShell>
  )
}
