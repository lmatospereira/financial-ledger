import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import { Box, Card, CardContent, Grid, Stack, Typography } from '@mui/material'
import type { Summary } from '../api/types'

interface BalanceCardProps {
  summary: Summary | null
  loading?: boolean
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

function formatCurrency(value: number): string {
  return currencyFormatter.format(value)
}

export default function BalanceCard({ summary, loading }: BalanceCardProps) {
  const incomeTotal = summary?.income_total ?? 0
  const expenseTotal = summary?.expense_total ?? 0
  const balance = summary?.balance ?? 0
  const previousBalance = summary?.previous_balance ?? 0

  return (
    <Card>
      <CardContent>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                }}
              >
                <AccountBalanceWalletIcon />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="body2" color="text.secondary">
                  Saldo atual
                </Typography>
                <Typography
                  variant="h5"
                  color={balance >= 0 ? 'success.main' : 'error.main'}
                  sx={{ fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {loading ? '—' : formatCurrency(balance)}
                </Typography>
              </Box>
            </Stack>
          </Grid>

          <Grid size={{ xs: 6, md: 2.67 }}>
            <Typography variant="body2" color="text.secondary">
              Saldo anterior
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {loading ? '—' : formatCurrency(previousBalance)}
            </Typography>
          </Grid>

          <Grid size={{ xs: 6, md: 2.67 }}>
            <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
              <ArrowUpwardIcon fontSize="small" color="success" />
              <Typography variant="body2" color="text.secondary">
                Receitas
              </Typography>
            </Stack>
            <Typography variant="h6" color="success.main" sx={{ fontWeight: 600 }}>
              {loading ? '—' : formatCurrency(incomeTotal)}
            </Typography>
          </Grid>

          <Grid size={{ xs: 6, md: 2.66 }}>
            <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
              <ArrowDownwardIcon fontSize="small" color="error" />
              <Typography variant="body2" color="text.secondary">
                Despesas
              </Typography>
            </Stack>
            <Typography variant="h6" color="error.main" sx={{ fontWeight: 600 }}>
              {loading ? '—' : formatCurrency(expenseTotal)}
            </Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
}
