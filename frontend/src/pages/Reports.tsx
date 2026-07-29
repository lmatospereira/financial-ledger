import { useCallback, useEffect, useMemo, useState } from 'react'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import { BarChart } from '@mui/x-charts/BarChart'
import { PieChart } from '@mui/x-charts/PieChart'
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  Typography,
  useTheme,
} from '@mui/material'
import MonthSelector from '../components/MonthSelector'
import Layout from '../components/Layout'
import {
  getApiErrorMessage,
  getCategoryBreakdown,
  getMonthlyTrend,
  getSummary,
} from '../api/client'
import type { CategoryBreakdownEntry, MonthlyTrendEntry, Summary } from '../api/types'

const MONTH_ABBREVIATIONS = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
]

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

function currentPeriod(): { month: number; year: number } {
  const now = new Date()
  return { month: now.getMonth() + 1, year: now.getFullYear() }
}

export default function Reports() {
  const theme = useTheme()
  const [{ month, year }, setPeriod] = useState(currentPeriod)

  const [summary, setSummary] = useState<Summary | null>(null)
  const [trend, setTrend] = useState<MonthlyTrendEntry[]>([])
  const [breakdown, setBreakdown] = useState<CategoryBreakdownEntry[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadPeriodData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, breakdownData] = await Promise.all([
        getSummary(month, year),
        getCategoryBreakdown(month, year),
      ])
      setSummary(summaryData)
      setBreakdown(breakdownData)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [month, year])

  const loadTrend = useCallback(async () => {
    try {
      const trendData = await getMonthlyTrend(year)
      setTrend(trendData)
    } catch (err) {
      setError((prev) => prev ?? getApiErrorMessage(err))
    }
  }, [year])

  useEffect(() => {
    loadPeriodData()
  }, [loadPeriodData])

  useEffect(() => {
    loadTrend()
  }, [loadTrend])

  const handleMonthChange = (nextMonth: number, nextYear: number) => {
    setPeriod({ month: nextMonth, year: nextYear })
  }

  const trendChartData = useMemo(() => {
    const byMonth = new Map(trend.map((entry) => [entry.month, entry]))
    return MONTH_ABBREVIATIONS.map((label, index) => {
      const entry = byMonth.get(index + 1)
      return {
        label,
        income: entry?.income_total ?? 0,
        expense: entry?.expense_total ?? 0,
      }
    })
  }, [trend])

  const pieData = useMemo(
    () =>
      breakdown
        .filter((entry) => entry.total > 0)
        .map((entry) => ({
          id: entry.category_id ?? 'none',
          value: entry.total,
          label: entry.name,
          color: entry.color,
        })),
    [breakdown],
  )

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Relatórios
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <MonthSelector month={month} year={year} onChange={handleMonthChange} />

        <Grid container spacing={2}>
          {/* Income Card */}
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 44,
                      height: 44,
                      borderRadius: '50%',
                      bgcolor: 'success.main',
                      color: 'white',
                    }}
                  >
                    <TrendingUpIcon />
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Receitas
                    </Typography>
                    <Typography variant="h6" color="success.main" sx={{ fontWeight: 700 }}>
                      {loading ? '—' : currencyFormatter.format(summary?.income_total ?? 0)}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          {/* Expense Card */}
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 44,
                      height: 44,
                      borderRadius: '50%',
                      bgcolor: 'error.main',
                      color: 'white',
                    }}
                  >
                    <TrendingDownIcon />
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Despesas
                    </Typography>
                    <Typography variant="h6" color="error.main" sx={{ fontWeight: 700 }}>
                      {loading ? '—' : currencyFormatter.format(summary?.expense_total ?? 0)}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          {/* Balance Card */}
          <Grid size={{ xs: 12, sm: 12, md: 4 }}>
            <Card>
              <CardContent>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 44,
                      height: 44,
                      borderRadius: '50%',
                      bgcolor: (summary?.balance ?? 0) >= 0 ? 'success.main' : 'error.main',
                      color: 'white',
                    }}
                  >
                    <AccountBalanceWalletIcon />
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Saldo
                    </Typography>
                    <Typography
                      variant="h6"
                      color={(summary?.balance ?? 0) >= 0 ? 'success.main' : 'error.main'}
                      sx={{ fontWeight: 700 }}
                    >
                      {loading ? '—' : currencyFormatter.format(summary?.balance ?? 0)}
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
              Receitas x despesas por mês ({year})
            </Typography>
            <BarChart
              height={320}
              dataset={trendChartData}
              xAxis={[{ scaleType: 'band', dataKey: 'label' }]}
              series={[
                {
                  dataKey: 'income',
                  label: 'Receitas',
                  color: theme.palette.success.main,
                  valueFormatter: (value: number | null) =>
                    currencyFormatter.format(value ?? 0),
                },
                {
                  dataKey: 'expense',
                  label: 'Despesas',
                  color: theme.palette.error.main,
                  valueFormatter: (value: number | null) =>
                    currencyFormatter.format(value ?? 0),
                },
              ]}
              slotProps={{ legend: { position: { vertical: 'top', horizontal: 'end' } } }}
              margin={{ top: 40 }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
              Despesas por categoria
            </Typography>
            {loading ? (
              <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
              </Box>
            ) : pieData.length === 0 ? (
              <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>
                <Typography variant="body1">
                  Nenhuma despesa registrada neste período.
                </Typography>
              </Box>
            ) : (
              <Grid container spacing={2} sx={{ alignItems: 'center' }}>
                <Grid size={{ xs: 12 }}>
                  <PieChart
                    height={320}
                    series={[
                      {
                        data: pieData,
                        innerRadius: 50,
                        paddingAngle: 2,
                        cornerRadius: 4,
                        valueFormatter: (item: { value: number }) =>
                          currencyFormatter.format(item.value),
                      },
                    ]}
                    slotProps={{
                      legend: { direction: 'vertical', position: { vertical: 'middle', horizontal: 'end' } },
                    }}
                  />
                </Grid>
              </Grid>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Layout>
  )
}
