import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { ArrowUp, Square } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled: boolean
  streaming: boolean
}

export function ChatInput({ onSend, disabled, streaming }: ChatInputProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [text])

  const handleSend = () => {
    if (!text.trim() || disabled || streaming) return
    onSend(text.trim())
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex items-end gap-2 bg-card border border-border rounded-xl px-3 py-2 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all shadow-sm">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question..."
        rows={1}
        className="flex-1 bg-transparent border-none outline-none resize-none text-sm leading-relaxed max-h-[160px] min-h-[22px] placeholder:text-muted-foreground/50 text-foreground"
        disabled={disabled}
      />
      <Button
        size="icon"
        onClick={streaming ? undefined : handleSend}
        disabled={(!text.trim() || disabled) && !streaming}
        className="shrink-0 rounded-lg h-8 w-8 transition-all"
      >
        {streaming ? (
          <Square className="h-4 w-4 fill-current" />
        ) : (
          <ArrowUp className="h-4 w-4" />
        )}
      </Button>
    </div>
  )
}
