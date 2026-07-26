import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProvider } from '@mui/material/styles'
import './index.css'
import App from './App.tsx'
import { ThemeModeProvider, useThemeMode } from './context/ThemeModeContext.tsx'
import { getTheme } from './theme.ts'
import { AuthProvider } from './context/AuthContext.tsx'

export function ThemedApp() {
  const { resolvedMode } = useThemeMode()
  const theme = getTheme(resolvedMode)

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeModeProvider>
      <ThemedApp />
    </ThemeModeProvider>
  </StrictMode>,
)
