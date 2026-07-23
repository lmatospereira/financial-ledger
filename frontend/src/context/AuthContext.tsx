import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { clearToken, getCurrentUser, getToken, setToken } from '../api/client'
import type { CurrentUser } from '../api/types'
import { AuthContext, type AuthContextValue } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [authLoading, setAuthLoading] = useState<boolean>(() => Boolean(getToken()))

  const loadCurrentUser = useCallback(async () => {
    setAuthLoading(true)
    try {
      const user = await getCurrentUser()
      setCurrentUser(user)
    } catch {
      // The response interceptor already clears the token and redirects to
      // /login on 401; nothing extra to do here.
      setCurrentUser(null)
    } finally {
      setAuthLoading(false)
    }
  }, [])

  // On app boot, if a token is already present in storage, resolve who the
  // user is before the rest of the app relies on `currentUser`. Reads the
  // token from storage directly (rather than the `token` state value) so
  // this effect only depends on the stable `loadCurrentUser` callback and
  // genuinely only runs once on mount — later token changes go through
  // signIn/signOut, which call loadCurrentUser directly.
  useEffect(() => {
    if (getToken()) {
      loadCurrentUser()
    }
  }, [loadCurrentUser])

  const signIn = useCallback(
    async (newToken: string) => {
      setToken(newToken)
      setTokenState(newToken)
      await loadCurrentUser()
    },
    [loadCurrentUser],
  )

  const signOut = useCallback(() => {
    clearToken()
    setTokenState(null)
    setCurrentUser(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(token),
      currentUser,
      authLoading,
      signIn,
      signOut,
    }),
    [token, currentUser, authLoading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
