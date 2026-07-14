import { useState } from 'react'
import { type Message } from '@/hooks/useChat'
import { Bot, User, Copy, Check, RefreshCw } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { SourceCitations } from './SourceCitations'

interface ChatMessageProps {
  message: Message
  isLast: boolean
}

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function ChatMessage({ message, isLast }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const isEmpty = !message.content && message.role === 'assistant' && isLast

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`group flex gap-3 px-1 py-3 md:py-4 animate-fade-slide-in ${isUser ? '' : 'bg-secondary/30 rounded-lg -mx-1 md:-mx-2 px-2 md:px-3'}`}>
      {/* Avatar */}
      <div className="flex-shrink-0 mt-0.5">
        {isUser ? (
          <div className="w-7 h-7 rounded-full bg-foreground/10 flex items-center justify-center">
            <User className="h-3.5 w-3.5 text-foreground/60" />
          </div>
        ) : (
          <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="h-3.5 w-3.5 text-primary" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-foreground/80">
            {isUser ? 'You' : 'GigaBot'}
          </span>
          <span className="text-[10px] text-muted-foreground/60">
            {formatTime(message.timestamp)}
          </span>
        </div>

        {/* Message body */}
        {isEmpty ? (
          <div className="flex items-center gap-1.5 text-muted-foreground/50">
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-dot" style={{ animationDelay: '0s' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-dot" style={{ animationDelay: '0.2s' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-dot" style={{ animationDelay: '0.4s' }} />
          </div>
        ) : (
          <div className="text-sm leading-relaxed text-foreground/90 prose prose-sm dark:prose-invert max-w-none">
            <MarkdownRenderer content={message.content} />
          </div>
        )}

        {/* Source citations */}
        {message.sources && message.sources.length > 0 && !isUser && (
          <div className="mt-3 animate-slide-up">
            <SourceCitations sources={message.sources} />
          </div>
        )}

        {/* Actions bar */}
        {message.content && !isUser && (
          <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-1 text-[11px] rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            >
              {copied ? (
                <><Check className="h-3 w-3" /> Copied</>
              ) : (
                <><Copy className="h-3 w-3" /> Copy</>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
