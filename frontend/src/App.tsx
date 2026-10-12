import { MESSAGES } from './messages'
import { StatusPage } from './pages/StatusPage'

export default function App() {
  return (
    <main className="app">
      <h1 className="app__title">{MESSAGES.appTitle}</h1>
      <StatusPage />
    </main>
  )
}
