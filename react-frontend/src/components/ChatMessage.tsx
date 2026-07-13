import { type Message } from '@/hooks/useChat'
import { Badge } from '@/components/ui/badge'
import { Bot, User } from 'lucide-react'

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
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.sources.map((s, i) => (
              <Badge
                key={i}
                variant="secondary"
                className="cursor-pointer hover:bg-primary/20 text-xs"
                onClick={() => onSourceClick(message.sources!)}
              >
                Source {i + 1}
                <span className="ml-1 opacity-60">{(s.score * 100).toFixed(0)}%</span>
              </Badge>
            ))}
          </div>
        )}

        <p className="text-[11px] text-muted-foreground mt-1 px-1">
          {formatTimestamp(message.timestamp)}
        </p>
      </div>
    </div>
  )
}
