import { useState, useEffect, useRef, useCallback } from 'react'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { useChat } from '@/hooks/useChat'
import { Sidebar } from '@/components/Sidebar'
import { ChatMessage } from '@/components/ChatMessage'
import { ChatInput } from '@/components/ChatInput'
import { WelcomeScreen } from '@/components/WelcomeScreen'
import { TypingIndicator } from '@/components/TypingIndicator'
import { UserMenu } from '@/components/auth/UserMenu'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { Menu, Sun, Moon } from 'lucide-react'

function usePathname() {
  const [pathname, setPathname] = useState(window.location.pathname)
  useEffect(() => {
    const handler = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])
  return pathname
}

function navigate(path: string) {
  window.history.pushState({}, '', path)
  window.dispatchEvent(new Event('popstate'))
}

function ChatApp() {
  const {
    sessions, currentSessionId, messages, isLoading, isStreaming, error,
    send, newSession, switchSession, deleteSession,
  } = useChat()

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  const scrollToBottom = useCallback(() => {
    const el = scrollContainerRef.current
    if (el) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight
      })
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isStreaming, scrollToBottom])

  const hasMessages = messages.length > 0
  const showWelcome = !isLoading && !hasMessages

  return (
    <ProtectedRoute>
      <div className="h-screen flex overflow-hidden bg-background">
        {sidebarOpen && (
          <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setSidebarOpen(false)} />
        )}
        <div className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 fixed md:relative z-50 md:z-auto transition-transform duration-200 ease-in-out`}>
          <Sidebar
            sessions={sessions}
            currentSessionId={currentSessionId}
            onNewSession={newSession}
            onSwitchSession={(id) => { switchSession(id); setSidebarOpen(false) }}
            onDeleteSession={deleteSession}
            onSuggestionClick={(text) => send(text)}
          />
          <div className="p-2 border-t border-border">
            <UserMenu />
          </div>
        </div>

        <div className="flex-1 flex flex-col min-w-0 relative">
          <header className="flex items-center gap-2 px-3 md:px-4 py-2.5 shrink-0 border-b bg-background/80 backdrop-blur-sm sticky top-0 z-30">
            <button className="md:hidden p-1.5 rounded-md hover:bg-secondary text-muted-foreground" onClick={() => setSidebarOpen(!sidebarOpen)}>
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-sm font-semibold text-foreground/80">GigaBot</h1>
            <div className="ml-auto flex items-center gap-1">
              <button onClick={() => setDark(!dark)} className="p-1.5 rounded-md hover:bg-secondary text-muted-foreground">
                {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
            </div>
          </header>

          <div ref={scrollContainerRef} className={`flex-1 overflow-y-auto scrollbar-thin ${showWelcome ? 'flex items-center justify-center' : ''}`}>
            <div className={`w-full ${hasMessages ? 'py-4 md:py-8 space-y-1' : 'py-0'}`}>
              {showWelcome && <WelcomeScreen onSuggestionClick={(text) => send(text)} />}
              {isLoading && !hasMessages && (
                <div className="flex justify-center py-20">
                  <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              )}
              <div className={`${hasMessages ? 'max-w-[var(--chat-width)] mx-auto px-3 md:px-4' : ''}`}>
                {messages.map((msg, i) => (
                  <ChatMessage key={msg.id} message={msg} isLast={i === messages.length - 1} />
                ))}
                {isStreaming && (
                  <div className="animate-fade-slide-in"><TypingIndicator /></div>
                )}
                {error && <div className="text-center text-destructive text-sm py-3 px-4 mx-auto max-w-md">{error}</div>}
              </div>
              <div ref={messagesEndRef} />
            </div>
          </div>

          <div className="shrink-0 border-t bg-background">
            <div className="max-w-[var(--chat-width)] mx-auto px-3 md:px-4 py-3">
              <ChatInput onSend={send} disabled={isLoading} streaming={isStreaming} />
              <p className="text-center text-[11px] text-muted-foreground/60 mt-2 select-none">
                Responses are AI-generated based on GigaCorp's knowledge base. Verify critical information.
              </p>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}

function Router() {
  const pathname = usePathname()

  if (pathname === '/login') return <LoginPage />
  if (pathname === '/register') return <RegisterPage />
  if (pathname === '/profile') return <ProfilePage />
  return <ChatApp />
}

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  )
}
