import { Activity, LogOut, MessageCircle, Wallet } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Failure } from '@/api/request'
import type { SessionUser } from '@/api/session'
import { Brand } from '@/components/Brand'
import { cn } from '@/lib/class-names'
import { MESSAGES } from '@/messages'

/** The screens of the menu. The menu is a state of the page, without a router (ADR 0027). */
export type Screen = 'accounts' | 'chat' | 'status'

export type LogoutFailure = Exclude<Failure['kind'], 'cancelled'>

const NAV = MESSAGES.nav

/** The dashboard once someone entered: the side menu, and the chosen screen next to it. */
export function AppShell({
  user,
  screen,
  onSelect,
  onLogout,
  logoutFailure,
  chatAvailable,
  children,
}: {
  user: SessionUser
  screen: Screen
  onSelect: (screen: Screen) => void
  onLogout: () => void
  // Why closing the session failed: the session is still alive, so the menu stays.
  logoutFailure: LogoutFailure | null
  // The web chat is a scaffold: its option exists only while the API has it on (ADR 0002).
  chatAvailable: boolean
  children: ReactNode
}) {
  return (
    <div className="min-h-screen md:grid md:grid-cols-[var(--sidebar-width)_1fr]">
      <aside className="flex flex-col gap-4 bg-sidebar px-4 py-4 text-sidebar-foreground md:min-h-screen md:py-6">
        <Brand inverted />
        <nav aria-label={NAV.label} className="flex flex-wrap gap-1 md:flex-col md:gap-4">
          <ul className="flex gap-1 md:flex-col">
            <NavItem current={screen === 'accounts'} onSelect={() => onSelect('accounts')} icon={<Wallet />}>
              {NAV.accounts}
            </NavItem>
          </ul>
          <div className="flex items-center gap-1 md:flex-col md:items-stretch">
            <p id="nav-testing" className="px-3 text-xs font-semibold tracking-wide text-sidebar-muted uppercase">
              {NAV.testing}
            </p>
            <ul aria-labelledby="nav-testing" className="flex gap-1 md:flex-col">
              {chatAvailable && (
                <NavItem current={screen === 'chat'} onSelect={() => onSelect('chat')} icon={<MessageCircle />}>
                  {NAV.chat}
                </NavItem>
              )}
              <NavItem current={screen === 'status'} onSelect={() => onSelect('status')} icon={<Activity />}>
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
            onClick={onLogout}
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
      <main className="mx-auto w-full max-w-3xl px-4 py-6 md:px-10 md:py-10">{children}</main>
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
