import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeModeContextType {
  mode: ThemeMode
  resolvedMode: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
}

const ThemeModeContext = createContext<ThemeModeContextType | undefined>(
  undefined,
)

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('themeMode')
    return (stored as ThemeMode) || 'system'
  })

  const [resolvedMode, setResolvedMode] = useState<'light' | 'dark'>('light')

  useEffect(() => {
    const resolveMode = () => {
      if (mode === 'system') {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        setResolvedMode(isDark ? 'dark' : 'light')
      } else {
        setResolvedMode(mode)
      }
    }

    resolveMode()

    if (mode === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = () => resolveMode()
      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [mode])

  const setMode = (newMode: ThemeMode) => {
    setModeState(newMode)
    localStorage.setItem('themeMode', newMode)
  }

  return (
    <ThemeModeContext.Provider value={{ mode, resolvedMode, setMode }}>
      {children}
    </ThemeModeContext.Provider>
  )
}

export function useThemeMode() {
  const context = useContext(ThemeModeContext)
  if (!context) {
    throw new Error('useThemeMode must be used within ThemeModeProvider')
  }
  return context
}
