import { useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import RepeatIcon from '@mui/icons-material/Repeat'
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
  Divider,
  Fab,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import {
  createRecurringTransaction,
  deleteRecurringTransaction,
  getAccounts,
  getApiErrorMessage,
  getCategories,
  getRecurringTransactions,
  updateRecurringTransaction,
} from '../api/client'
import type {
  Account,
  Category,
  RecurringTransaction,
  RecurringTransactionInput,
  RecurringTransactionUpdate,
} from '../api/types'
import { MAX_AMOUNT } from '../constants'
import { getDateGuardrails } from '../utils/dateGuardrails'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const emptyForm: RecurringTransactionInput = {
  account_id: 0,
  category_id: null,
  description: '',
  amount: 0,
  type: 'expense',
  day_of_month: 1,
  start_date: new Date().toISOString().split('T')[0],
  end_date: null,
}

export default function Recurring() {
  const [recurring, setRecurring] = useState<RecurringTransaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<RecurringTransaction | null>(null)
  const [form, setForm] = useState<RecurringTransactionInput>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<RecurringTransaction | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [recurringData, accountsData, categoriesData] = await Promise.all([
        getRecurringTransactions(),
        getAccounts(),
        getCategories(),
      ])
      setRecurring(recurringData)
      setAccounts(accountsData)
      setCategories(categoriesData)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const openCreateForm = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (rule: RecurringTransaction) => {
    setEditing(rule)
    setForm({
      account_id: rule.account_id,
      category_id: rule.category_id,
      description: rule.description,
      amount: rule.amount,
      type: rule.type,
      day_of_month: rule.day_of_month,
      start_date: rule.start_date,
      end_date: rule.end_date,
    })
    setFormError(null)
    setFormOpen(true)
  }

  const dateGuardrails = getDateGuardrails()

  const handleSubmit = async () => {
    setFormError(null)
    if (!form.account_id) {
      setFormError('Selecione uma conta.')
      return
    }
    if (!form.description.trim()) {
      setFormError('Informe uma descrição.')
      return
    }
    if (form.amount <= 0) {
      setFormError('Informe um valor maior que zero.')
      return
    }
    if (form.amount > MAX_AMOUNT) {
      setFormError(`Informe um valor menor que ${MAX_AMOUNT.toLocaleString('pt-BR')}.`)
      return
    }
    if (form.day_of_month < 1 || form.day_of_month > 31) {
      setFormError('O dia do mês deve estar entre 1 e 31.')
      return
    }

    setSubmitting(true)
    try {
      if (editing) {
        await updateRecurringTransaction(editing.id, {
          ...form,
          active: editing.active,
        } as RecurringTransactionUpdate)
      } else {
        await createRecurringTransaction(form)
      }
      setFormOpen(false)
      await loadData()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const toggleActive = async (rule: RecurringTransaction) => {
    try {
      await updateRecurringTransaction(rule.id, {
        ...rule,
        active: !rule.active,
      })
      await loadData()
    } catch (err) {
      setError(getApiErrorMessage(err))
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteRecurringTransaction(pendingDelete.id)
      setPendingDelete(null)
      await loadData()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  const filteredCategories = categories.filter((c) => c.type === form.type)

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Lançamentos Recorrentes
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <Card>
          {loading ? (
            <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : recurring.length === 0 ? (
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <RepeatIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">Nenhuma regra recorrente definida.</Typography>
            </Box>
          ) : (
            <List disablePadding>
              {recurring.map((rule, index) => {
                const account = accounts.find((a) => a.id === rule.account_id)
                const category = categories.find((c) => c.id === rule.category_id)
                return (
                  <Box key={rule.id}>
                    {index > 0 && <Divider component="li" />}
                    <ListItem
                      sx={{ py: 1.5 }}
                      secondaryAction={
                        <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
                          <Switch
                            edge="end"
                            checked={rule.active}
                            onChange={() => toggleActive(rule)}
                            size="small"
                          />
                          <IconButton
                            aria-label="Editar"
                            size="small"
                            onClick={() => openEditForm(rule)}
                          >
                            <EditOutlinedIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            aria-label="Excluir"
                            size="small"
                            onClick={() => setPendingDelete(rule)}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      }
                    >
                      <ListItemText
                        primary={rule.description}
                        secondary={
                          <Stack spacing={0.5}>
                            <Typography variant="caption" color="text.secondary">
                              {rule.type === 'income' ? '+' : '−'}{' '}
                              {currencyFormatter.format(rule.amount)} • Dia {rule.day_of_month}
                              {rule.end_date
                                ? ` • Até ${new Date(rule.end_date).toLocaleDateString('pt-BR')}`
                                : ''}
                            </Typography>
                            <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                              {account && (
                                <Typography variant="caption" sx={{ color: account.color }}>
                                  {account.name}
                                </Typography>
                              )}
                              {category && (
                                <Typography
                                  variant="caption"
                                  sx={{
                                    bgcolor: category.color,
                                    color: 'white',
                                    px: 0.75,
                                    py: 0.25,
                                    borderRadius: 0.5,
                                  }}
                                >
                                  {category.name}
                                </Typography>
                              )}
                            </Stack>
                          </Stack>
                        }
                      />
                    </ListItem>
                  </Box>
                )
              })}
            </List>
          )}
        </Card>
      </Stack>

      <Fab
        color="primary"
        aria-label="Adicionar regra recorrente"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>
          {editing ? 'Editar lançamento recorrente' : 'Novo lançamento recorrente'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              select
              label="Conta"
              value={form.account_id || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, account_id: Number(e.target.value) }))
              }
              fullWidth
              autoFocus={!editing}
            >
              {accounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Tipo"
              value={form.type}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  type: e.target.value as RecurringTransactionInput['type'],
                }))
              }
              fullWidth
            >
              <MenuItem value="income">Receita</MenuItem>
              <MenuItem value="expense">Despesa</MenuItem>
            </TextField>

            <TextField
              select
              label="Categoria (opcional)"
              value={form.category_id || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  category_id: e.target.value ? Number(e.target.value) : null,
                }))
              }
              fullWidth
            >
              <MenuItem value="">— Sem categoria —</MenuItem>
              {filteredCategories.map((category) => (
                <MenuItem key={category.id} value={category.id}>
                  {category.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Descrição"
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
              fullWidth
              multiline
              rows={2}
            />

            <TextField
              label="Valor"
              inputMode="decimal"
              placeholder="0,00"
              value={form.amount || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, amount: Number(e.target.value) }))
              }
              fullWidth
              slotProps={{
                input: {
                  inputProps: {
                    max: MAX_AMOUNT,
                    min: 0.01,
                    step: 0.01,
                  },
                },
              }}
            />

            <TextField
              label="Dia do mês (1-31)"
              type="number"
              value={form.day_of_month}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, day_of_month: Number(e.target.value) }))
              }
              fullWidth
            />

            <TextField
              label="Data de início"
              type="date"
              value={form.start_date}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, start_date: e.target.value }))
              }
              fullWidth
              slotProps={{
                inputLabel: { shrink: true },
                input: {
                  inputProps: {
                    min: dateGuardrails.min,
                    max: dateGuardrails.max,
                  },
                },
              }}
            />

            <TextField
              label="Data de término (opcional)"
              type="date"
              value={form.end_date || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, end_date: e.target.value || null }))
              }
              fullWidth
              slotProps={{
                inputLabel: { shrink: true },
                input: {
                  inputProps: {
                    min: dateGuardrails.min,
                    max: dateGuardrails.max,
                  },
                },
              }}
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
        <DialogTitle>Excluir lançamento recorrente?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja excluir a regra "{pendingDelete?.description}"? Essa
            ação não pode ser desfeita.
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
