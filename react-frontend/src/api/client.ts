import axios from 'axios'

const API_BASE = '/api/v1'

export interface SourceCitation {
  content: string
  score: number
  source: string
  metadata: Record<string, string | number>
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

// ── Auth Types ──

export interface UserResponse {
  id: string
  email: string
  username: string
  display_name: string | null
  role: string
  is_verified: boolean
  avatar_url: string | null
  company: string | null
  phone: string | null
  created_at: string | null
  last_login_at: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserResponse
}

// ── Axios Instance ──

let accessToken: string | null = localStorage.getItem('gc_access_token')
let refreshToken: string | null = localStorage.getItem('gc_refresh_token')
let refreshPromise: Promise<void> | null = null

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error?.config
    if (error?.response?.status === 401 && !original?._retry && refreshToken) {
      original._retry = true
      try {
        await refreshAccessToken()
        original.headers.Authorization = `Bearer ${accessToken}`
        return api(original)
      } catch {
        clearTokens()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
  localStorage.setItem('gc_access_token', access)
  localStorage.setItem('gc_refresh_token', refresh)
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
  localStorage.removeItem('gc_access_token')
  localStorage.removeItem('gc_refresh_token')
  localStorage.removeItem('gc_user')
}

export function getStoredUser(): UserResponse | null {
  try {
    const raw = localStorage.getItem('gc_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function storeUser(user: UserResponse) {
  localStorage.setItem('gc_user', JSON.stringify(user))
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const res = await axios.post<TokenResponse>(`${API_BASE}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      setTokens(res.data.access_token, res.data.refresh_token)
      storeUser(res.data.user)
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

// ── Auth API ──

export async function register(
  email: string,
  username: string,
  password: string,
  displayName?: string
): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/register', {
    email, username, password,
    display_name: displayName,
  })
  setTokens(res.data.access_token, res.data.refresh_token)
  storeUser(res.data.user)
  return res.data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/login', { email, password })
  setTokens(res.data.access_token, res.data.refresh_token)
  storeUser(res.data.user)
  return res.data
}

export async function logout() {
  const stored = localStorage.getItem('gc_refresh_token')
  if (stored) {
    try {
      await api.post('/auth/logout', { refresh_token: stored })
    } catch { /* ignore */ }
  }
  clearTokens()
}

export async function getProfile(): Promise<UserResponse> {
  const res = await api.get<UserResponse>('/auth/me')
  return res.data
}

export async function updateProfile(data: {
  display_name?: string
  company?: string
  phone?: string
  avatar_url?: string
}): Promise<UserResponse> {
  const res = await api.patch<UserResponse>('/auth/me', data)
  storeUser(res.data)
  return res.data
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export async function requestPasswordReset(email: string) {
  await api.post('/auth/request-password-reset', { email })
}

// ── Chat API ──

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
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`
      }

      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers,
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
