import { useCallback, useEffect, useMemo, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined'
import RepeatIcon from '@mui/icons-material/Repeat'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import TuneIcon from '@mui/icons-material/Tune'
import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Fab,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import BalanceCard from '../components/BalanceCard'
import Layout from '../components/Layout'
import MonthSelector from '../components/MonthSelector'
import TransactionForm from '../components/TransactionForm'
import TransactionList from '../components/TransactionList'
import TransferDialog from '../components/TransferDialog'
import {
  confirmTransaction,
  createTransaction,
  deleteTransaction,
  getAccounts,
  getApiErrorMessage,
  getCategories,
  getCurrentUser,
  getUpcomingAlerts,
  getSummary,
  getTransactions,
  updateDashboardPreferences,
  updateTransaction,
} from '../api/client'
import type { Account, Category, Summary, Transaction, TransactionInput, UpcomingAlert } from '../api/types'

function currentPeriod(): { month: number; year: number } {
  const now = new Date()
  return { month: now.getMonth() + 1, year: now.getFullYear() }
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

function getDaysUntilDue(dueDate: string): number {
  const due = new Date(dueDate)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  due.setHours(0, 0, 0, 0)
  return Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function formatRelativeDueDate(daysUntilDue: number): string {
  if (daysUntilDue < 0) return `Atrasado ${Math.abs(daysUntilDue)} dias`
  if (daysUntilDue === 0) return 'Hoje'
  if (daysUntilDue === 1) return 'Amanhã'
  return `em ${daysUntilDue} dias`
}

function getAlertKindIcon(kind: 'bill' | 'recurring' | 'installment') {
  switch (kind) {
    case 'bill':
      return <ReceiptLongOutlinedIcon fontSize="small" />
    case 'recurring':
      return <RepeatIcon fontSize="small" />
    case 'installment':
      return <CreditCardIcon fontSize="small" />
  }
}

export default function Dashboard() {
  const [{ month, year }, setPeriod] = useState(currentPeriod)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [accountFilter, setAccountFilter] = useState<number | ''>('')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [upcomingAlerts, setUpcomingAlerts] = useState<UpcomingAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [hiddenWidgets, setHiddenWidgets] = useState<string[]>([])
  const [draftHiddenWidgets, setDraftHiddenWidgets] = useState<string[]>([])
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false)
  const [savingPreferences, setSavingPreferences] = useState(false)

  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'confirmed'>('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(
    null,
  )
  const [transferOpen, setTransferOpen] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const accountId = accountFilter === '' ? undefined : accountFilter
      const [transactionsData, categoriesData, summaryData, accountsData, alertsData] =
        await Promise.all([
          getTransactions(month, year, accountId),
          getCategories(),
          getSummary(month, year, accountId),
          getAccounts(),
          getUpcomingAlerts(7),
        ])
      setTransactions(transactionsData)
      setCategories(categoriesData)
      setSummary(summaryData)
      setAccounts(accountsData)
      setUpcomingAlerts(alertsData)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [month, year, accountFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    const fetchDashboardPreferences = async () => {
      try {
        const user = await getCurrentUser()
        setHiddenWidgets(user.dashboard_hidden_widgets || [])
      } catch (err) {
        console.error('Failed to fetch dashboard preferences:', err)
      }
    }
    fetchDashboardPreferences()
  }, [])

  const handleMonthChange = (nextMonth: number, nextYear: number) => {
    setPeriod({ month: nextMonth, year: nextYear })
  }

  const openCreateForm = () => {
    setEditingTransaction(null)
    setFormOpen(true)
  }

  const openEditForm = (transaction: Transaction) => {
    setEditingTransaction(transaction)
    setFormOpen(true)
  }

  const handleFormSubmit = async (payload: TransactionInput) => {
    if (editingTransaction) {
      await updateTransaction(editingTransaction.id, payload)
    } else {
      await createTransaction(payload)
    }
    setFormOpen(false)
    await loadData()
  }

  const handleDelete = async (transaction: Transaction) => {
    await deleteTransaction(transaction.id)
    await loadData()
  }

  const handleConfirm = async (transaction: Transaction, accountId: number) => {
    await confirmTransaction(transaction.id, accountId)
    await loadData()
  }

  const openSettingsDialog = () => {
    setDraftHiddenWidgets(hiddenWidgets)
    setSettingsDialogOpen(true)
  }

  const handleSavePreferences = async () => {
    setSavingPreferences(true)
    try {
      await updateDashboardPreferences(draftHiddenWidgets)
      setHiddenWidgets(draftHiddenWidgets)
      setSettingsDialogOpen(false)
    } catch (err) {
      console.error('Failed to save preferences:', err)
    } finally {
      setSavingPreferences(false)
    }
  }

  const toggleDraftWidget = (widgetName: string) => {
    setDraftHiddenWidgets((prev) =>
      prev.includes(widgetName)
        ? prev.filter((w) => w !== widgetName)
        : [...prev, widgetName],
    )
  }

  const filteredTransactions = useMemo(() => {
    let result = transactions

    // Filter by category
    if (activeCategoryId !== null) {
      result = result.filter((t) => t.category_id === activeCategoryId)
    }

    // Filter by status
    if (statusFilter !== 'all') {
      result = result.filter((t) => t.status === statusFilter)
    }

    return result
  }, [transactions, activeCategoryId, statusFilter])

  return (
    <Layout>
      <Stack spacing={3}>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <MonthSelector month={month} year={year} onChange={handleMonthChange} />
          <IconButton
            aria-label="Preferências do dashboard"
            onClick={openSettingsDialog}
            size="small"
          >
            <TuneIcon />
          </IconButton>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        {!hiddenWidgets.includes('balance') && (
          <BalanceCard summary={summary} loading={loading} />
        )}

        {!hiddenWidgets.includes('alerts') && upcomingAlerts.length > 0 && (
          <Card>
            <Box sx={{ px: 2, pt: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                Próximos vencimentos (7 dias)
              </Typography>
            </Box>
            <List disablePadding>
              {upcomingAlerts.slice(0, 5).map((alert) => {
                const daysUntilDue = getDaysUntilDue(alert.due_date)
                return (
                  <ListItem
                    key={`${alert.kind}-${alert.id}`}
                    sx={{
                      py: 1.5,
                      px: 2,
                      borderTop: '1px solid',
                      borderColor: 'divider',
                      '&:first-of-type': {
                        borderTop: 'none',
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Box
                        sx={{
                          color: alert.is_overdue ? 'error.main' : 'text.secondary',
                        }}
                      >
                        {getAlertKindIcon(alert.kind)}
                      </Box>
                    </ListItemIcon>
                    <ListItemText
                      primary={alert.description}
                      secondary={
                        <Stack spacing={0.5} direction="row" sx={{ alignItems: 'center', mt: 0.5 }}>
                          <Chip
                            label={formatRelativeDueDate(daysUntilDue)}
                            size="small"
                            variant="outlined"
                            color={alert.is_overdue ? 'error' : 'default'}
                            sx={{ height: 20, fontSize: 11 }}
                          />
                          {alert.account && (
                            <Chip
                              label={alert.account.name}
                              size="small"
                              sx={{
                                bgcolor: alert.account.color,
                                color: 'white',
                                height: 20,
                                fontSize: 11,
                              }}
                            />
                          )}
                        </Stack>
                      }
                    />
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        color: alert.is_overdue ? 'error.main' : 'text.primary',
                        minWidth: 'fit-content',
                        ml: 2,
                      }}
                    >
                      {currencyFormatter.format(alert.amount)}
                    </Typography>
                  </ListItem>
                )
              })}
            </List>
            {upcomingAlerts.length > 5 && (
              <Box sx={{ px: 2, py: 1, textAlign: 'center', borderTop: '1px solid', borderColor: 'divider' }}>
                <Typography variant="caption" color="text.secondary">
                  +{upcomingAlerts.length - 5} outros vencimentos
                </Typography>
              </Box>
            )}
          </Card>
        )}

        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
        >
          <TextField
            select
            size="small"
            label="Conta"
            value={accountFilter}
            onChange={(e) =>
              setAccountFilter(e.target.value === '' ? '' : Number(e.target.value))
            }
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="">
              <em>Todas as contas</em>
            </MenuItem>
            {accounts.map((account) => (
              <MenuItem key={account.id} value={account.id}>
                {account.name}
              </MenuItem>
            ))}
          </TextField>

          <Button
            variant="outlined"
            startIcon={<SwapHorizIcon />}
            onClick={() => setTransferOpen(true)}
            disabled={accounts.length < 2}
          >
            Nova transferência
          </Button>
        </Stack>

        {categories.length > 0 && (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
              <Chip
                label="Todas"
                color={activeCategoryId === null ? 'primary' : 'default'}
                onClick={() => setActiveCategoryId(null)}
              />
              {categories.map((category) => (
                <Chip
                  key={category.id}
                  label={category.name}
                  onClick={() => setActiveCategoryId(category.id)}
                  sx={{
                    bgcolor: activeCategoryId === category.id ? category.color : undefined,
                    color: activeCategoryId === category.id ? 'white' : undefined,
                    borderColor: category.color,
                  }}
                  variant={activeCategoryId === category.id ? 'filled' : 'outlined'}
                />
              ))}
            </Stack>
          </Stack>
        )}

        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
          <Chip
            label="Todas"
            color={statusFilter === 'all' ? 'primary' : 'default'}
            onClick={() => setStatusFilter('all')}
          />
          <Chip
            label="Pendentes"
            color={statusFilter === 'pending' ? 'warning' : 'default'}
            onClick={() => setStatusFilter('pending')}
            variant={statusFilter === 'pending' ? 'filled' : 'outlined'}
          />
          <Chip
            label="Confirmadas"
            color={statusFilter === 'confirmed' ? 'success' : 'default'}
            onClick={() => setStatusFilter('confirmed')}
            variant={statusFilter === 'confirmed' ? 'filled' : 'outlined'}
          />
        </Stack>

        <Card>
          <Box sx={{ px: 2, pt: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Lançamentos
            </Typography>
          </Box>
          {loading ? (
            <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : (
            <TransactionList
              transactions={filteredTransactions}
              accounts={accounts}
              onEdit={openEditForm}
              onDelete={handleDelete}
              onConfirm={handleConfirm}
            />
          )}
        </Card>
      </Stack>

      <Fab
        color="primary"
        aria-label="Adicionar lançamento"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <TransactionForm
        open={formOpen}
        categories={categories}
        accounts={accounts}
        initialValue={editingTransaction}
        defaultAccountId={accountFilter === '' ? null : accountFilter}
        onClose={() => setFormOpen(false)}
        onSubmit={handleFormSubmit}
        onInstallmentSuccess={async () => {
          setFormOpen(false)
          await loadData()
        }}
      />

      <TransferDialog
        open={transferOpen}
        accounts={accounts}
        onClose={() => setTransferOpen(false)}
        onSuccess={async () => {
          setTransferOpen(false)
          await loadData()
        }}
      />

      <Dialog open={settingsDialogOpen} onClose={() => setSettingsDialogOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Preferências do Dashboard</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={!draftHiddenWidgets.includes('balance')}
                  onChange={() => toggleDraftWidget('balance')}
                />
              }
              label="Mostrar saldo"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={!draftHiddenWidgets.includes('alerts')}
                  onChange={() => toggleDraftWidget('alerts')}
                />
              }
              label="Mostrar próximos vencimentos"
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setSettingsDialogOpen(false)} disabled={savingPreferences}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleSavePreferences} disabled={savingPreferences}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </Layout>
  )
}
