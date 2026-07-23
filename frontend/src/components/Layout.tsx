import type { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import LogoutIcon from '@mui/icons-material/Logout'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import {
  AppBar,
  Box,
  Button,
  Container,
  IconButton,
  Stack,
  Toolbar,
  Typography,
} from '@mui/material'
import { useAuth } from '../context/authContext'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { signOut } = useAuth()

  const handleLogout = () => {
    signOut()
    navigate('/login', { replace: true })
  }

  return (
    <Box sx={{ minHeight: '100%', bgcolor: 'background.default' }}>
      <AppBar position="sticky" color="inherit" sx={{ bgcolor: 'background.paper' }}>
        <Toolbar sx={{ gap: 1 }}>
          <AccountBalanceWalletIcon color="primary" />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            Livro Caixa
          </Typography>
          <Stack direction="row" spacing={1} sx={{ display: { xs: 'none', sm: 'flex' } }}>
            <Button
              onClick={() => navigate('/')}
              variant={location.pathname === '/' ? 'contained' : 'text'}
              size="small"
            >
              Lançamentos
            </Button>
            <Button
              onClick={() => navigate('/categories')}
              variant={location.pathname === '/categories' ? 'contained' : 'text'}
              size="small"
            >
              Categorias
            </Button>
          </Stack>
          <IconButton
            aria-label="Sair"
            onClick={handleLogout}
            sx={{ display: { xs: 'inline-flex', sm: 'none' } }}
          >
            <LogoutIcon />
          </IconButton>
          <Button
            onClick={handleLogout}
            startIcon={<LogoutIcon />}
            color="inherit"
            size="small"
            sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
          >
            Sair
          </Button>
        </Toolbar>
        <Stack
          direction="row"
          spacing={1}
          sx={{ display: { xs: 'flex', sm: 'none' }, px: 2, pb: 1 }}
        >
          <Button
            onClick={() => navigate('/')}
            variant={location.pathname === '/' ? 'contained' : 'text'}
            size="small"
            fullWidth
          >
            Lançamentos
          </Button>
          <Button
            onClick={() => navigate('/categories')}
            variant={location.pathname === '/categories' ? 'contained' : 'text'}
            size="small"
            fullWidth
          >
            Categorias
          </Button>
        </Stack>
      </AppBar>
      <Container maxWidth="md" sx={{ py: { xs: 2, sm: 4 } }}>
        {children}
      </Container>
    </Box>
  )
}
