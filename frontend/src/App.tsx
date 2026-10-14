import { useCallback, useState } from 'react'
import type { SessionUser } from './api/session'
import { MESSAGES } from './messages'
import { AccountsPage } from './pages/AccountsPage'
import { DevEntryPage } from './pages/DevEntryPage'
import { StatusPage } from './pages/StatusPage'

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  // Changing it starts the entry again, to show it when the session ended on its own.
  const [entry, setEntry] = useState(0)
  const sessionEnded = useCallback(() => {
    setUser(null)
    setEntry((current) => current + 1)
  }, [])

  return (
    <main className="app">
      <h1 className="app__title">{MESSAGES.appTitle}</h1>
      {/* With a session, the accounts are the first thing seen (FEAT-001, CA-13). */}
      {user && <AccountsPage key={user.id} onNoSession={sessionEnded} />}
      <StatusPage />
      <DevEntryPage key={entry} onSessionChange={setUser} />
    </main>
  )
}
