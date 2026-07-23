import { createContext, useContext } from 'react'

export interface AuthContextValue {
  isAuthenticated: boolean
  signIn: (token: string) => void
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
