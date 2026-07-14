import { useState, useCallback, useRef, useEffect } from 'react'
import {
  type SSEEvent,
  type SessionInfo,
  type SourceCitation,
  type MessageEntry,
  streamChat,
  sendMessage,
  createSession,
  listSessions,
  deleteSession as apiDeleteSession,
  getHistory,
} from '@/api/client'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceCitation[]
  timestamp: string
}

const TITLE_CACHE_KEY = 'gc_chat_titles'
const MAX_TITLE_LEN = 40

function loadTitles(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(TITLE_CACHE_KEY) || '{}')
  } catch {
    return {}
  }
}

function saveTitles(titles: Record<string, string>) {
  localStorage.setItem(TITLE_CACHE_KEY, JSON.stringify(titles))
}

function generateTitle(text: string): string {
  const clean = text.replace(/[^a-zA-Z0-9\s?.,!-]/g, '').trim()
  if (clean.length <= MAX_TITLE_LEN) return clean
  return clean.slice(0, clean.lastIndexOf(' ', MAX_TITLE_LEN)) + '…'
}

export function useChat() {
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [titles, setTitles] = useState<Record<string, string>>(loadTitles)
  const abortRef = useRef<(() => void) | null>(null)
  const msgIdCounter = useRef(0)

  const nextId = () => `msg_${++msgIdCounter.current}`

  const updateTitle = useCallback((sessionId: string, text: string) => {
    setTitles((prev) => {
      if (prev[sessionId]) return prev
      const updated = { ...prev, [sessionId]: generateTitle(text) }
      saveTitles(updated)
      return updated
    })
  }, [])

  const loadSessions = useCallback(async () => {
    try {
      const list = await listSessions()
      setSessions(list)
    } catch (e) {
      console.error('Failed to load sessions', e)
    }
  }, [])

  const ensureSession = useCallback(async () => {
    if (currentSessionId) return currentSessionId
    const session = await createSession()
    setCurrentSessionId(session.session_id)
    setSessions((prev) => [session, ...prev])
    return session.session_id
  }, [currentSessionId])

  const switchSession = useCallback(async (sessionId: string) => {
    abortRef.current?.()
    setCurrentSessionId(sessionId)
    setIsLoading(true)
    setError(null)
    setMessages([])
    try {
      const history = await getHistory(sessionId, 100)
      const loaded: Message[] = history.map((m: MessageEntry) => ({
        id: nextId(),
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: m.timestamp,
      }))
      setMessages(loaded)
    } catch {
      setMessages([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  const newSession = useCallback(async () => {
    abortRef.current?.()
    const session = await createSession()
    setCurrentSessionId(session.session_id)
    setMessages([])
    setError(null)
    setSessions((prev) => [session, ...prev])
    return session.session_id
  }, [])

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return
      setError(null)

      const sid = await ensureSession()
      const userMsg: Message = {
        id: nextId(),
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      updateTitle(sid, text)

      const assistantMsg: Message = {
        id: nextId(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setIsStreaming(true)

      abortRef.current = streamChat(
        sid,
        text,
        (event: SSEEvent) => {
          if (event.type === 'token' && event.content) {
            setMessages((prev) => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') {
                copy[copy.length - 1] = { ...last, content: last.content + event.content }
              }
              return copy
            })
          } else if (event.type === 'sources' && event.sources) {
            setMessages((prev) => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last && last.role === 'assistant') {
                copy[copy.length - 1] = { ...last, sources: event.sources }
              }
              return copy
            })
          }
        },
        (err: Error) => {
          setError(err.message)
          setIsStreaming(false)
          setMessages((prev) => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.role === 'assistant' && !last.content) {
              copy[copy.length - 1] = { ...last, content: `Error: ${err.message}` }
            }
            return copy
          })
        },
        () => {
          setIsStreaming(false)
          setSessions((prev) =>
            prev.map((s) =>
              s.session_id === sid
                ? { ...s, message_count: s.message_count + 2 }
                : s
            )
          )
        }
      )
    },
    [ensureSession, isStreaming, updateTitle]
  )

  const deleteSessionById = useCallback(
    async (sessionId: string) => {
      await apiDeleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null)
        setMessages([])
      }
    },
    [currentSessionId]
  )

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    return () => {
      abortRef.current?.()
    }
  }, [])

  return {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    isStreaming,
    error,
    send,
    newSession,
    switchSession,
    deleteSession: deleteSessionById,
    loadSessions,
    titles,
  }
}
