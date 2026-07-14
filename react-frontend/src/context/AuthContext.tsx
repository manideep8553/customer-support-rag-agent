import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import {
  type UserResponse,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getProfile,
  getStoredUser,
  storeUser,
  clearTokens,
} from '@/api/client'

interface AuthContextType {
  user: UserResponse | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string, displayName?: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(getStoredUser)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const profile = await getProfile()
      setUser(profile)
      storeUser(profile)
    } catch {
      setUser(null)
      clearTokens()
    }
  }, [])

  useEffect(() => {
    const stored = getStoredUser()
    if (stored) {
      setUser(stored)
      refreshUser().finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [refreshUser])

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password)
    setUser(res.user)
  }, [])

  const register = useCallback(async (
    email: string, username: string, password: string, displayName?: string
  ) => {
    const res = await apiRegister(email, username, password, displayName)
    setUser(res.user)
  }, [])

  const logout = useCallback(async () => {
    await apiLogout()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
