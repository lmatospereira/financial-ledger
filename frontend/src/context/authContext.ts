import { createContext, useContext } from 'react'
import type { CurrentUser } from '../api/types'

export interface AuthContextValue {
  isAuthenticated: boolean
  // `undefined` while /api/auth/me hasn't resolved yet (token present but
  // profile not loaded), `null` when there's no session at all.
  currentUser: CurrentUser | null
  authLoading: boolean
  signIn: (token: string) => Promise<void>
  signOut: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
