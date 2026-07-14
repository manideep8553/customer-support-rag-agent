import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { User, Settings, LogOut, ChevronDown } from 'lucide-react'

export function UserMenu() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)

  if (!user) return null

  const initial = (user.display_name || user.username || user.email)[0].toUpperCase()

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-secondary/50 transition-colors text-left"
      >
        <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary flex-shrink-0">
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-foreground/80 truncate">
            {user.display_name || user.username}
          </div>
          <div className="text-[10px] text-muted-foreground/60 truncate">{user.email}</div>
        </div>
        <ChevronDown className={`h-3 w-3 text-muted-foreground/60 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute bottom-full left-0 right-0 mb-1 z-50 bg-card border border-border rounded-xl shadow-lg overflow-hidden">
            <a
              href="/profile"
              className="flex items-center gap-2 px-3 py-2 text-sm text-foreground/80 hover:bg-secondary/50 transition-colors"
              onClick={() => setOpen(false)}
            >
              <Settings className="h-3.5 w-3.5" />
              Profile Settings
            </a>
            <button
              onClick={() => { setOpen(false); logout() }}
              className="flex items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/5 transition-colors w-full text-left"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  )
}
