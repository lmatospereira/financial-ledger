import { useCallback, useEffect, useMemo, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Fab,
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
  createTransaction,
  deleteTransaction,
  getAccounts,
  getApiErrorMessage,
  getCategories,
  getSummary,
  getTransactions,
  updateTransaction,
} from '../api/client'
import type { Account, Category, Summary, Transaction, TransactionInput } from '../api/types'

function currentPeriod(): { month: number; year: number } {
  const now = new Date()
  return { month: now.getMonth() + 1, year: now.getFullYear() }
}

export default function Dashboard() {
  const [{ month, year }, setPeriod] = useState(currentPeriod)
  const [accounts, setAccounts] = useState<Account[]>([])
  const [accountFilter, setAccountFilter] = useState<number | ''>('')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null)
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
      const [transactionsData, categoriesData, summaryData, accountsData] =
        await Promise.all([
          getTransactions(month, year, accountId),
          getCategories(),
          getSummary(month, year, accountId),
          getAccounts(),
        ])
      setTransactions(transactionsData)
      setCategories(categoriesData)
      setSummary(summaryData)
      setAccounts(accountsData)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [month, year, accountFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

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

  const filteredTransactions = useMemo(() => {
    if (activeCategoryId === null) return transactions
    return transactions.filter((t) => t.category_id === activeCategoryId)
  }, [transactions, activeCategoryId])

  return (
    <Layout>
      <Stack spacing={3}>
        <MonthSelector month={month} year={year} onChange={handleMonthChange} />

        {error && <Alert severity="error">{error}</Alert>}

        <BalanceCard summary={summary} loading={loading} />

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
        )}

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
              onEdit={openEditForm}
              onDelete={handleDelete}
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
    </Layout>
  )
}
