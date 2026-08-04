import { createTheme, type Theme } from '@mui/material/styles'

export function getTheme(mode: 'light' | 'dark'): Theme {
  const isLight = mode === 'light'

  return createTheme({
    palette: {
      mode,
      primary: {
        main: isLight ? '#2196f3' : '#2196f3',
        light: isLight ? '#e3f2fd' : '#e3f2fd',
        dark: isLight ? '#1e88e5' : '#1e88e5',
        contrastText: '#FFFFFF',
      },
      secondary: {
        main: isLight ? '#673ab7' : '#7c4dff',
        light: isLight ? '#ede7f6' : '#d1c4e9',
        dark: isLight ? '#5e35b1' : '#651fff',
        contrastText: isLight ? '#673ab7' : '#ffffff',
      },
      success: {
        main: isLight ? '#00e676' : '#00e676',
      },
      error: {
        main: isLight ? '#f44336' : '#f44336',
      },
      background: {
        default: isLight ? '#f8fafc' : '#1a223f',
        paper: isLight ? '#ffffff' : '#111936',
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
            paddingLeft: 24,
            paddingRight: 24,
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
