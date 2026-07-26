import { useState, type ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import KeyOutlinedIcon from '@mui/icons-material/KeyOutlined'
import LogoutIcon from '@mui/icons-material/Logout'
import PersonOutlineIcon from '@mui/icons-material/PersonOutlineOutlined'
import LightModeIcon from '@mui/icons-material/LightMode'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Container,
  Divider,
  IconButton,
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

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { signOut, currentUser } = useAuth()
  const { resolvedMode, setMode } = useThemeMode()

  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null)
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)

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
    { label: 'Relatórios', path: '/reports' },
    ...(currentUser?.is_admin ? [{ label: 'Usuários', path: '/users' }] : []),
  ]

  return (
    <Box sx={{ minHeight: '100%', bgcolor: 'background.default' }}>
      <AppBar position="sticky" color="inherit" sx={{ bgcolor: 'background.paper' }}>
        <Toolbar sx={{ gap: 1 }}>
          <AccountBalanceWalletIcon color="primary" />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            Livro Caixa
          </Typography>
          <Stack
            direction="row"
            spacing={1}
            sx={{ display: { xs: 'none', md: 'flex' } }}
          >
            {navItems.map((item) => (
              <Button
                key={item.path}
                onClick={() => navigate(item.path)}
                variant={location.pathname === item.path ? 'contained' : 'text'}
                size="small"
              >
                {item.label}
              </Button>
            ))}
          </Stack>

          <IconButton
            aria-label="Conta"
            onClick={(e) => setMenuAnchor(e.currentTarget)}
            size="small"
            sx={{ ml: 1 }}
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
              {currentUser?.username.slice(0, 1).toUpperCase() ?? <PersonOutlineIcon fontSize="small" />}
            </Avatar>
          </IconButton>
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
        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          sx={{ display: { xs: 'flex', md: 'none' }, flexWrap: 'wrap', px: 2, pb: 1 }}
        >
          {navItems.map((item) => (
            <Button
              key={item.path}
              onClick={() => navigate(item.path)}
              variant={location.pathname === item.path ? 'contained' : 'text'}
              size="small"
            >
              {item.label}
            </Button>
          ))}
        </Stack>
      </AppBar>
      <Container maxWidth="md" sx={{ py: { xs: 2, sm: 4 } }}>
        {children}
      </Container>

      <ChangePasswordDialog
        open={passwordDialogOpen}
        onClose={() => setPasswordDialogOpen(false)}
      />
    </Box>
  )
}
