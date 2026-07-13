import { useState, useEffect, useRef } from 'react'
import { useChat } from '@/hooks/useChat'
import { Sidebar } from '@/components/Sidebar'
import { ChatMessage } from '@/components/ChatMessage'
import { ChatInput } from '@/components/ChatInput'
import { WelcomeScreen } from '@/components/WelcomeScreen'
import { SourceModal } from '@/components/SourceModal'
import { TypingIndicator } from '@/components/TypingIndicator'
import { type SourceCitation } from '@/api/client'
import { Menu, Monitor, Loader2 } from 'lucide-react'

export default function App() {
  const {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    isStreaming,
    error,
    send,
    newSession,
    switchSession,
    deleteSession,
  } = useChat()

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sourceModalOpen, setSourceModalOpen] = useState(false)
  const [selectedSources, setSelectedSources] = useState<SourceCitation[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  const handleSourceClick = (sources: SourceCitation[]) => {
    setSelectedSources(sources)
    setSourceModalOpen(true)
  }

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 fixed md:relative z-50 md:z-auto transition-transform duration-200`}
      >
        <Sidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onNewSession={newSession}
          onSwitchSession={switchSession}
          onDeleteSession={deleteSession}
        />
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center gap-3 px-4 md:px-6 py-3 border-b bg-card shrink-0">
          <button
            className="md:hidden p-1.5 rounded-md hover:bg-secondary text-muted-foreground"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-base font-semibold">Customer Support</h1>
            <p className="text-xs text-muted-foreground hidden sm:block">
              GigaCorp AI RAG Agent — Ask me anything about our products and policies
            </p>
          </div>
          <div className="ml-auto">
            {currentSessionId && (
              <span className="text-xs text-muted-foreground bg-secondary px-3 py-1.5 rounded-full">
                {currentSessionId.slice(0, 8)}...
              </span>
            )}
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 scrollbar-thin">
          {isLoading && !messages.length && (
            <div className="flex justify-center items-center h-full">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {!isLoading && messages.length === 0 && !currentSessionId && (
            <WelcomeScreen onSuggestionClick={(text) => send(text)} />
          )}

          {!isLoading && messages.length === 0 && currentSessionId && (
            <WelcomeScreen onSuggestionClick={(text) => send(text)} />
          )}

          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              message={msg}
              onSourceClick={handleSourceClick}
            />
          ))}

          {isStreaming && !messages[messages.length - 1]?.content && (
            <TypingIndicator />
          )}

          {error && (
            <div className="text-center text-destructive text-sm py-4">{error}</div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <ChatInput
          onSend={send}
          disabled={isLoading}
          streaming={isStreaming}
        />
      </div>

      {/* Source Modal */}
      <SourceModal
        open={sourceModalOpen}
        onOpenChange={setSourceModalOpen}
        sources={selectedSources}
      />
    </div>
  )
}
