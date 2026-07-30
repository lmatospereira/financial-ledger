import { createTheme, type Theme } from '@mui/material/styles'

export function getTheme(mode: 'light' | 'dark'): Theme {
  const isLight = mode === 'light'

  return createTheme({
    palette: {
      mode,
      primary: {
        main: isLight ? '#820AD1' : '#C084F5',
        light: isLight ? '#A040E8' : '#D4A7FF',
        dark: isLight ? '#6A088D' : '#9D5FD4',
        contrastText: '#FFFFFF',
      },
      secondary: {
        main: isLight ? '#F5E6FF' : '#3D2255',
        light: isLight ? '#F5E6FF' : '#5A3878',
        contrastText: isLight ? '#820AD1' : '#C084F5',
      },
      success: {
        main: isLight ? '#16A34A' : '#4ADE80',
      },
      error: {
        main: isLight ? '#DC2626' : '#F87171',
      },
      background: {
        default: isLight ? '#FAFAFA' : '#121016',
        paper: isLight ? '#FFFFFF' : '#1C1922',
      },
      divider: isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.08)',
    },
    shape: {
      borderRadius: 20,
    },
    typography: {
      fontFamily: [
        'Nunito',
        'Roboto',
        '"Helvetica Neue"',
        'Arial',
        'sans-serif',
      ].join(','),
      h1: { fontWeight: 800 },
      h2: { fontWeight: 800 },
      h3: { fontWeight: 800 },
      h4: { fontWeight: 800 },
      h5: { fontWeight: 700 },
      h6: { fontWeight: 700 },
      button: { textTransform: 'none', fontWeight: 700 },
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
              : '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: isLight ? '0 1px 3px rgba(0, 0, 0, 0.06)' : 'none',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 999,
            paddingX: 3,
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
            fontWeight: 600,
            borderRadius: 999,
          },
        },
      },
    },
  })
}

export const lightTheme = getTheme('light')
export const darkTheme = getTheme('dark')
