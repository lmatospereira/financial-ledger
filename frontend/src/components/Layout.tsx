import { useState, type ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTheme, useMediaQuery, alpha } from '@mui/material'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import KeyOutlinedIcon from '@mui/icons-material/KeyOutlined'
import LogoutIcon from '@mui/icons-material/Logout'
import PersonOutlineIcon from '@mui/icons-material/PersonOutlineOutlined'
import LightModeIcon from '@mui/icons-material/LightMode'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import MenuIcon from '@mui/icons-material/Menu'
import {
  AppBar,
  Avatar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Stack,
  Toolbar,
  Typography,
} from '@mui/material'
import ChangePasswordDialog from './ChangePasswordDialog'
import { useAuth } from '../context/authContext'
import { useThemeMode } from '../context/ThemeModeContext'

interface LayoutProps {
  children: ReactNode
}

interface NavItem {
  label: string
  path: string
}

const SIDEBAR_WIDTH = 280

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const { signOut, currentUser } = useAuth()
  const { resolvedMode, setMode } = useThemeMode()

  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null)
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    setMenuAnchor(null)
    signOut()
    navigate('/login', { replace: true })
  }

  const handleThemeToggle = () => {
    if (resolvedMode === 'light') {
      setMode('dark')
    } else {
      setMode('light')
    }
  }

  const navItems: NavItem[] = [
    { label: 'Lançamentos', path: '/' },
    { label: 'Contas', path: '/accounts' },
    { label: 'Categorias', path: '/categories' },
    { label: 'Orçamento', path: '/budgets' },
    { label: 'Recorrentes', path: '/recurring' },
    { label: 'Contas a Pagar', path: '/bills' },
    { label: 'Cartões', path: '/cards' },
    { label: 'Metas', path: '/goals' },
    { label: 'Investimentos', path: '/investments' },
    { label: 'Relatórios', path: '/reports' },
    ...(currentUser?.is_admin ? [{ label: 'Usuários', path: '/users' }] : []),
  ]

  const handleNavClick = (path: string) => {
    navigate(path)
    if (isMobile) {
      setSidebarOpen(false)
    }
  }

  // Sidebar content (shared between permanent and temporary drawer)
  const sidebarContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo section */}
      <Box
        sx={{
          px: 2,
          py: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <AccountBalanceWalletIcon color="primary" sx={{ fontSize: 28 }} />
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.light} 100%)`,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Livro Caixa
        </Typography>
      </Box>

      {/* Navigation menu */}
      <List sx={{ flex: 1, px: 1, py: 2 }}>
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <ListItemButton
              key={item.path}
              onClick={() => handleNavClick(item.path)}
              selected={isActive}
              sx={{
                mb: 0.5,
                borderRadius: 2,
                px: 2,
                py: 1.25,
                color: isActive ? 'primary.main' : 'text.primary',
                backgroundColor: isActive ? alpha(theme.palette.primary.main, 0.12) : 'transparent',
                fontWeight: isActive ? 600 : 500,
                '&:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.08),
                },
              }}
            >
              <ListItemText primary={item.label} />
            </ListItemButton>
          )
        })}
      </List>

      {/* Footer info */}
      <Box
        sx={{
          px: 2,
          py: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
          textAlign: 'center',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {currentUser && `Conectado como ${currentUser.username}`}
        </Typography>
      </Box>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Top AppBar */}
      <AppBar
        position="fixed"
        color="inherit"
        sx={{
          bgcolor: 'background.paper',
          width: { xs: '100%', md: `calc(100% - ${SIDEBAR_WIDTH}px)` },
          ml: { xs: 0, md: `${SIDEBAR_WIDTH}px` },
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Toolbar sx={{ gap: 2 }}>
          {/* Menu toggle for mobile */}
          <IconButton
            aria-label="Toggle sidebar"
            onClick={() => setSidebarOpen(true)}
            size="small"
            sx={{ display: { xs: 'flex', md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          {/* Spacer */}
          <Box sx={{ flex: 1 }} />

          {/* User profile menu */}
          <Stack direction="row" spacing={1}>
            <IconButton
              aria-label="User menu"
              onClick={(e) => setMenuAnchor(e.currentTarget)}
              size="small"
            >
              <Avatar
                sx={{
                  width: 36,
                  height: 36,
                  bgcolor: 'primary.main',
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                {currentUser?.username.slice(0, 1).toUpperCase() ?? (
                  <PersonOutlineIcon fontSize="small" />
                )}
              </Avatar>
            </IconButton>
          </Stack>

          <Menu
            anchorEl={menuAnchor}
            open={Boolean(menuAnchor)}
            onClose={() => setMenuAnchor(null)}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          >
            {currentUser && (
              <Box sx={{ px: 2, py: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {currentUser.username}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {currentUser.is_admin ? 'Administrador' : 'Usuário'}
                </Typography>
              </Box>
            )}
            <Divider />
            <MenuItem onClick={handleThemeToggle}>
              <ListItemIcon>
                {resolvedMode === 'light' ? (
                  <DarkModeIcon fontSize="small" />
                ) : (
                  <LightModeIcon fontSize="small" />
                )}
              </ListItemIcon>
              <ListItemText>
                {resolvedMode === 'light' ? 'Modo escuro' : 'Modo claro'}
              </ListItemText>
            </MenuItem>
            <MenuItem
              onClick={() => {
                setMenuAnchor(null)
                setPasswordDialogOpen(true)
              }}
            >
              <ListItemIcon>
                <KeyOutlinedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Alterar senha</ListItemText>
            </MenuItem>
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Sair</ListItemText>
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Sidebar - Permanent on desktop, Temporary on mobile */}
      <Box component="nav" sx={{ width: { xs: 'auto', md: SIDEBAR_WIDTH }, flexShrink: { md: 0 } }}>
        {isMobile ? (
          // Temporary drawer for mobile
          <Drawer
            anchor="left"
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            slotProps={{
              paper: {
                sx: {
                  width: SIDEBAR_WIDTH,
                  bgcolor: 'background.paper',
                  borderRight: `1px solid ${theme.palette.divider}`,
                },
              },
            }}
          >
            {sidebarContent}
          </Drawer>
        ) : (
          // Permanent drawer for desktop
          <Drawer
            variant="permanent"
            anchor="left"
            slotProps={{
              paper: {
                sx: {
                  position: 'fixed',
                  width: SIDEBAR_WIDTH,
                  height: '100vh',
                  bgcolor: 'background.paper',
                  borderRight: `1px solid ${theme.palette.divider}`,
                },
              },
            }}
            sx={{
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
              },
            }}
          >
            {sidebarContent}
          </Drawer>
        )}
      </Box>

      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          mt: 8,
          minHeight: '100vh',
        }}
      >
        {/* Content */}
        <Box
          sx={{
            flex: 1,
            p: { xs: 2, sm: 3 },
            overflow: 'auto',
          }}
        >
          {children}
        </Box>
      </Box>

      <ChangePasswordDialog
        open={passwordDialogOpen}
        onClose={() => setPasswordDialogOpen(false)}
      />
    </Box>
  )
}
