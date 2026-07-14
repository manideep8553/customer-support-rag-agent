import { useState, useMemo } from 'react'
import { type SessionInfo } from '@/api/client'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Plus, MessageSquare, Trash2, Search,
  Package, RotateCcw, DollarSign, Clock, Crown,
} from 'lucide-react'

interface SidebarProps {
  sessions: SessionInfo[]
  currentSessionId: string | null
  onNewSession: () => void
  onSwitchSession: (id: string) => void
  onDeleteSession: (id: string) => void
  onSuggestionClick: (text: string) => void
}

const QUICK_ACTIONS = [
  { label: 'Shipping', icon: Package, query: 'What are your shipping options and delivery times?' },
  { label: 'Returns', icon: RotateCcw, query: 'What is your return and refund policy?' },
  { label: 'Pricing', icon: DollarSign, query: 'How much does GigaAnalytics cost?' },
  { label: 'Hours', icon: Clock, query: 'What are your business hours and support availability?' },
  { label: 'Premium', icon: Crown, query: 'Tell me about Premium support plans' },
]

function formatDate(ts: string): string {
  try {
    const d = new Date(ts)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    const days = Math.floor(diff / 86400000)
    if (days === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    if (days === 1) return 'Yesterday'
    if (days < 7) return d.toLocaleDateString([], { weekday: 'short' })
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewSession,
  onSwitchSession,
  onDeleteSession,
  onSuggestionClick,
}: SidebarProps) {
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!search.trim()) return sessions
    const q = search.toLowerCase()
    return sessions.filter((s) => s.session_id.toLowerCase().includes(q))
  }, [sessions, search])

  return (
    <aside className="w-72 h-full bg-sidebar text-sidebar-foreground flex flex-col shrink-0">
      {/* Header */}
      <div className="p-3 border-b border-sidebar-border">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center text-sm font-bold text-primary-foreground">
            G
          </div>
          <span className="text-base font-semibold tracking-tight">GigaBot</span>
        </div>
        <Button
          size="sm"
          className="w-full justify-start bg-sidebar-hover hover:bg-sidebar-active text-sidebar-foreground border border-sidebar-border"
          onClick={onNewSession}
        >
          <Plus className="h-4 w-4 mr-2" />
          New chat
        </Button>
      </div>

      {/* Quick actions */}
      <div className="px-2 py-2 border-b border-sidebar-border">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40 px-2 mb-1.5">
          Quick Actions
        </p>
        <div className="flex flex-wrap gap-1">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => onSuggestionClick(action.query)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] rounded-md bg-sidebar-hover hover:bg-sidebar-active text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
            >
              <action.icon className="h-3 w-3" />
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-sidebar-hover text-sidebar-foreground/50 text-sm">
          <Search className="h-3.5 w-3.5 shrink-0" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className="bg-transparent border-none outline-none text-sm text-sidebar-foreground placeholder:text-sidebar-foreground/40 w-full"
          />
        </div>
      </div>

      {/* Sessions */}
      <ScrollArea className="flex-1 px-2 py-1">
        {filtered.length === 0 && (
          <p className="text-center text-sidebar-foreground/30 text-xs py-8">
            {search ? 'No matching conversations' : 'No conversations yet'}
          </p>
        )}
        {filtered.map((session) => (
          <div
            key={session.session_id}
            className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer text-sm mb-0.5 transition-colors ${
              currentSessionId === session.session_id
                ? 'bg-sidebar-active text-sidebar-foreground'
                : 'text-sidebar-foreground/70 hover:bg-sidebar-hover'
            }`}
            onClick={() => onSwitchSession(session.session_id)}
          >
            <MessageSquare className="h-4 w-4 shrink-0 opacity-40" />
            <div className="flex-1 min-w-0">
              <div className="truncate text-xs">
                {session.message_count > 0
                  ? `Conversation ${session.session_id.slice(-6)}`
                  : 'New conversation'}
              </div>
              <div className="text-[10px] text-sidebar-foreground/40 mt-0.5">
                {session.message_count} messages · {formatDate(session.last_active)}
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSession(session.session_id)
              }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-destructive/20 hover:text-destructive transition-all"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        ))}
      </ScrollArea>

      {/* Footer */}
      <div className="p-3 border-t border-sidebar-border">
        <div className="flex items-center gap-2 text-xs text-sidebar-foreground/40">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          AI Support · {sessions.length} conversations
        </div>
      </div>
    </aside>
  )
}
