import { type SessionInfo } from '@/api/client'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Plus, MessageSquare, Trash2, Monitor } from 'lucide-react'

interface SidebarProps {
  sessions: SessionInfo[]
  currentSessionId: string | null
  onNewSession: () => void
  onSwitchSession: (id: string) => void
  onDeleteSession: (id: string) => void
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewSession,
  onSwitchSession,
  onDeleteSession,
}: SidebarProps) {
  return (
    <aside className="w-72 bg-sidebar text-sidebar-foreground flex flex-col shrink-0">
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2.5 mb-4">
          <Monitor className="h-7 w-7 text-indigo-400" />
          <span className="text-lg font-bold tracking-tight">GigaCorp</span>
        </div>
        <Button
          variant="outline"
          className="w-full border-white/20 text-white hover:bg-sidebar-hover bg-transparent"
          onClick={onNewSession}
        >
          <Plus className="h-4 w-4 mr-2" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="flex-1 p-2">
        {sessions.length === 0 && (
          <p className="text-center text-white/40 text-sm py-8">No conversations yet</p>
        )}
        {sessions.map((session) => (
          <div
            key={session.session_id}
            className={`group flex items-center gap-2 px-3 py-2.5 rounded-md cursor-pointer text-sm mb-0.5 transition-colors ${
              currentSessionId === session.session_id
                ? 'bg-sidebar-active text-white'
                : 'text-white/70 hover:bg-sidebar-hover'
            }`}
            onClick={() => onSwitchSession(session.session_id)}
          >
            <MessageSquare className="h-4 w-4 shrink-0 opacity-50" />
            <span className="truncate flex-1">
              {session.message_count > 0
                ? `Conversation ${session.session_id.slice(-8)}`
                : 'New conversation'}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSession(session.session_id)
              }}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 hover:text-red-400 transition-all"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </ScrollArea>

      <div className="p-3 border-t border-white/10 text-xs text-white/50 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        AI Support Agent
      </div>
    </aside>
  )
}
