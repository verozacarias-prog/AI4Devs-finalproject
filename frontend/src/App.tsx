import { MESSAGES } from './messages'
import { DevEntryPage } from './pages/DevEntryPage'
import { StatusPage } from './pages/StatusPage'

export default function App() {
  return (
    <main className="app">
      <h1 className="app__title">{MESSAGES.appTitle}</h1>
      <StatusPage />
      <DevEntryPage />
    </main>
  )
}
