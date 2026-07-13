import axios from 'axios'

const API_BASE = '/api/v1'

export interface SourceCitation {
  content: string
  score: number
  source: string
}

export interface ChatResponse {
  session_id: string
  answer: string
  sources: SourceCitation[]
  timestamp: string
}

export interface SessionInfo {
  session_id: string
  message_count: number
  created_at: string
  last_active: string
}

export interface MessageEntry {
  role: string
  content: string
  timestamp: string
}

export interface SSEEvent {
  type: 'token' | 'sources' | 'done'
  content?: string
  sources?: SourceCitation[]
  session_id?: string
}

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

export async function createSession(sessionId?: string): Promise<SessionInfo> {
  const body = sessionId ? { session_id: sessionId } : {}
  const res = await api.post<SessionInfo>('/sessions', body)
  return res.data
}

export async function listSessions(): Promise<SessionInfo[]> {
  const res = await api.get<SessionInfo[]>('/sessions')
  return res.data
}

export async function getSession(sessionId: string): Promise<SessionInfo> {
  const res = await api.get<SessionInfo>(`/sessions/${sessionId}`)
  return res.data
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/sessions/${sessionId}`)
}

export async function getHistory(
  sessionId: string,
  limit = 50
): Promise<MessageEntry[]> {
  const res = await api.post<{ session_id: string; messages: MessageEntry[] }>(
    `/sessions/${sessionId}/history`,
    { session_id: sessionId, limit }
  )
  return res.data.messages
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>('/chat', {
    session_id: sessionId,
    message,
  })
  return res.data
}

export function streamChat(
  sessionId: string,
  message: string,
  onEvent: (event: SSEEvent) => void,
  onError: (error: Error) => void,
  onComplete: () => void
): () => void {
  let aborted = false

  const run = async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Stream error' }))
        onError(new Error(err.detail || 'Stream error'))
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        onError(new Error('No response body'))
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (!aborted) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as SSEEvent
              onEvent(data)
              if (data.type === 'done') {
                onComplete()
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      }
    } catch (err) {
      if (!aborted) {
        onError(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  run()
  return () => {
    aborted = true
  }
}

export async function reingest(filePath?: string): Promise<{
  status: string
  chunks_ingested: number
  message: string
}> {
  const body = filePath ? { file_path: filePath } : {}
  const res = await api.post('/ingest', body)
  return res.data
}

export async function healthCheck(): Promise<{
  status: string
  knowledge_base: { initialized: boolean; chunk_count: number }
  timestamp: string
}> {
  const res = await api.get('/health')
  return res.data
}
