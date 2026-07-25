import { useCallback, useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import {
  Alert,
  Box,
  Button,
  Card,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Fab,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import MonthSelector from '../components/MonthSelector'
import {
  createBudget,
  deleteBudget,
  getApiErrorMessage,
  getBudgets,
  getBudgetStatus,
  getCategories,
  updateBudget,
} from '../api/client'
import type { Budget, BudgetInput, BudgetStatus, Category } from '../api/types'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const emptyForm: BudgetInput = {
  category_id: 0,
  amount: 0,
}

function currentPeriod(): { month: number; year: number } {
  const now = new Date()
  return { month: now.getMonth() + 1, year: now.getFullYear() }
}

function getProgressColor(overBudget: boolean, percentage: number): 'success' | 'warning' | 'error' {
  if (overBudget) return 'error'
  if (percentage >= 70) return 'warning'
  return 'success'
}

export default function Budgets() {
  const [{ month, year }, setPeriod] = useState(currentPeriod)
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Budget | null>(null)
  const [form, setForm] = useState<BudgetInput>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<Budget | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [budgetsData, statusData, categoriesData] = await Promise.all([
        getBudgets(),
        getBudgetStatus(month, year),
        getCategories(),
      ])
      setBudgets(budgetsData)
      setBudgetStatus(statusData)
      setCategories(categoriesData)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [month, year])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleMonthChange = (nextMonth: number, nextYear: number) => {
    setPeriod({ month: nextMonth, year: nextYear })
  }

  const openCreateForm = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (budget: Budget) => {
    setEditing(budget)
    setForm({ category_id: budget.category_id, amount: budget.amount })
    setFormError(null)
    setFormOpen(true)
  }

  const handleSubmit = async () => {
    setFormError(null)
    if (!form.category_id) {
      setFormError('Selecione uma categoria.')
      return
    }
    if (form.amount <= 0) {
      setFormError('Informe um valor maior que zero.')
      return
    }

    setSubmitting(true)
    try {
      if (editing) {
        await updateBudget(editing.id, form)
      } else {
        await createBudget(form)
      }
      setFormOpen(false)
      await loadData()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteBudget(pendingDelete.id)
      setPendingDelete(null)
      await loadData()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  // Categories not already budgeted
  const availableCategories = categories.filter(
    (cat) => cat.type === 'expense' && !budgets.some((b) => b.category_id === cat.id),
  )
  // If editing, also include the current category
  const editableCategories = editing
    ? [
        ...availableCategories,
        categories.find((c) => c.id === editing.category_id),
      ].filter(Boolean) as Category[]
    : availableCategories

  return (
    <Layout>
      <Stack spacing={3}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
        >
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Orçamento
          </Typography>
        </Stack>

        <MonthSelector month={month} year={year} onChange={handleMonthChange} />

        {error && <Alert severity="error">{error}</Alert>}

        <Card>
          {loading ? (
            <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : budgetStatus.length === 0 ? (
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <TrendingDownIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">Nenhum orçamento definido.</Typography>
            </Box>
          ) : (
            <List disablePadding>
              {budgetStatus.map((status, index) => (
                <ListItem
                  key={status.category_id}
                  sx={{ py: 2, borderTop: index > 0 ? 1 : 0, borderColor: 'divider' }}
                  secondaryAction={
                    <Stack direction="row" spacing={0.5}>
                      <IconButton
                        aria-label="Editar"
                        size="small"
                        onClick={() => {
                          const budget = budgets.find(
                            (b) => b.category_id === status.category_id,
                          )
                          if (budget) openEditForm(budget)
                        }}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        aria-label="Excluir"
                        size="small"
                        onClick={() => {
                          const budget = budgets.find(
                            (b) => b.category_id === status.category_id,
                          )
                          if (budget) setPendingDelete(budget)
                        }}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  }
                >
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      bgcolor: status.category_color,
                      mr: 2,
                      flexShrink: 0,
                    }}
                  />
                  <ListItemText
                    primary={status.category_name}
                    secondary={
                      <Stack spacing={1} sx={{ mt: 1 }}>
                        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                          <Box sx={{ flexGrow: 1 }}>
                            <LinearProgress
                              variant="determinate"
                              value={Math.min(status.percentage, 100)}
                              color={getProgressColor(status.over_budget, status.percentage)}
                              sx={{ height: 8, borderRadius: 1 }}
                            />
                          </Box>
                          <Typography variant="caption" sx={{ minWidth: 60, textAlign: 'right' }}>
                            {status.percentage.toFixed(0)}%
                          </Typography>
                        </Stack>
                        <Typography variant="caption" color="text.secondary">
                          {currencyFormatter.format(status.spent_amount)} de{' '}
                          {currencyFormatter.format(status.budget_amount)}
                        </Typography>
                      </Stack>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Card>
      </Stack>

      <Fab
        color="primary"
        aria-label="Adicionar orçamento"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editing ? 'Editar orçamento' : 'Novo orçamento'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              select
              label="Categoria"
              value={form.category_id || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, category_id: Number(e.target.value) }))
              }
              fullWidth
              disabled={editing !== null}
            >
              {editableCategories.map((category) => (
                <MenuItem key={category.id} value={category.id}>
                  {category.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Limite mensal"
              inputMode="decimal"
              placeholder="0,00"
              value={form.amount || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, amount: Number(e.target.value) }))
              }
              fullWidth
              autoFocus={!editing}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setFormOpen(false)} disabled={submitting}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)}>
        <DialogTitle>Excluir orçamento?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja remover o orçamento da categoria "
            {pendingDelete
              ? categories.find((c) => c.id === pendingDelete.category_id)?.name
              : ''}
            "? Essa ação não pode ser desfeita.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setPendingDelete(null)} disabled={deleting}>
            Cancelar
          </Button>
          <Button color="error" variant="contained" onClick={confirmDelete} disabled={deleting}>
            Excluir
          </Button>
        </DialogActions>
      </Dialog>
    </Layout>
  )
}
