import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { api, getToken, setToken, type Me, type RegisterData } from './api'

interface AuthState {
  me: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    // Без токена спрашивать «кто я» незачем — сразу показываем вход.
    if (!getToken()) {
      setMe(null)
      setLoading(false)
      return
    }
    try {
      setMe(await api.get<Me>('/api/auth/me'))
    } catch {
      setMe(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    // Если токен протух посреди работы, возвращаемся на экран входа.
    const onLogout = () => setMe(null)
    window.addEventListener('logout', onLogout)
    return () => window.removeEventListener('logout', onLogout)
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.post<{ access_token: string }>('/api/auth/login', {
        email,
        password,
      })
      setToken(response.access_token)
      await refresh()
    },
    [refresh],
  )

  const register = useCallback(
    async (data: RegisterData) => {
      const response = await api.post<{ access_token: string }>('/api/auth/register', data)
      setToken(response.access_token)
      await refresh()
    },
    [refresh],
  )

  const logout = useCallback(() => {
    setToken(null)
    setMe(null)
  }, [])

  const value = useMemo(
    () => ({ me, loading, login, register, logout, refresh }),
    [me, loading, login, register, logout, refresh],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth должен использоваться внутри AuthProvider')
  return context
}
