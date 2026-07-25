import { createTheme, type Theme } from '@mui/material/styles'

export function getTheme(mode: 'light' | 'dark'): Theme {
  const isLight = mode === 'light'

  return createTheme({
    palette: {
      mode,
      primary: {
        main: isLight ? '#4F46E5' : '#818CF8',
        light: isLight ? '#6366F1' : '#A5B4FC',
        dark: isLight ? '#4338CA' : '#6366F1',
        contrastText: '#FFFFFF',
      },
      secondary: {
        main: isLight ? '#0D9488' : '#2DD4BF',
        light: isLight ? '#14B8A6' : '#2DD4BF',
        contrastText: '#FFFFFF',
      },
      success: {
        main: isLight ? '#16A34A' : '#4ADE80',
      },
      error: {
        main: isLight ? '#DC2626' : '#F87171',
      },
      background: {
        default: isLight ? '#F7F8FC' : '#0F1115',
        paper: isLight ? '#FFFFFF' : '#171A21',
      },
      divider: isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.08)',
    },
    shape: {
      borderRadius: 16,
    },
    typography: {
      fontFamily: [
        'Inter',
        'Roboto',
        '"Helvetica Neue"',
        'Arial',
        'sans-serif',
      ].join(','),
      h1: { fontWeight: 700 },
      h2: { fontWeight: 700 },
      h3: { fontWeight: 700 },
      h4: { fontWeight: 700 },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            border: isLight
              ? '1px solid rgba(0, 0, 0, 0.06)'
              : 'rgba(255, 255, 255, 0.08)',
            boxShadow: isLight ? '0 1px 3px rgba(0, 0, 0, 0.06)' : 'none',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 10,
          },
        },
      },
      MuiAppBar: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            borderBottom: isLight
              ? '1px solid rgba(0, 0, 0, 0.06)'
              : '1px solid rgba(255, 255, 255, 0.08)',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            fontWeight: 500,
          },
        },
      },
    },
  })
}

export const lightTheme = getTheme('light')
export const darkTheme = getTheme('dark')
