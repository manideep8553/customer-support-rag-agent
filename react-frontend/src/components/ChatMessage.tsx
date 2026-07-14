import { type Message } from '@/hooks/useChat'
import { type SourceCitation } from '@/api/client'
import { Bot, User, ChevronRight } from 'lucide-react'

interface ChatMessageProps {
  message: Message
  onSourceClick: (sources: NonNullable<Message['sources']>) => void
}

function formatTimestamp(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function sourceMeta(s: SourceCitation) {
  const m = s.metadata || {}
  return {
    heading: (m.heading as string) || '',
    doc: (m.source as string) || s.source || 'Document',
  }
}

export function ChatMessage({ message, onSourceClick }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 mb-6 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-indigo-100 text-primary'
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={`max-w-[85%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-sm'
              : 'bg-secondary text-foreground rounded-bl-sm'
          }`}
        >
          {message.content || (message.role === 'assistant' ? '...' : '')}
        </div>

        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-1">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Sources
            </p>
            {message.sources.map((s, i) => {
              const meta = sourceMeta(s)
              return (
                <button
                  key={i}
                  onClick={() => onSourceClick(message.sources!)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-muted/50 border border-border hover:border-primary/40 hover:bg-primary/5 transition-colors text-left cursor-pointer"
                >
                  <span className="w-5 h-5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                    {i + 1}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-xs font-medium truncate">
                      {meta.heading || 'Untitled Section'}
                    </span>
                    <span className="block text-[10px] text-muted-foreground truncate">
                      {meta.doc}
                    </span>
                  </span>
                  <span className="text-[10px] font-semibold text-primary flex-shrink-0">
                    {(s.score * 100).toFixed(0)}%
                  </span>
                  <ChevronRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                </button>
              )
            })}
          </div>
        )}

        <p className="text-[11px] text-muted-foreground mt-1 px-1">
          {formatTimestamp(message.timestamp)}
        </p>
      </div>
    </div>
  )
}
