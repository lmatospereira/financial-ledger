import { useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import ReceiptOutlinedIcon from '@mui/icons-material/ReceiptOutlined'
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
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
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import {
  createBill,
  deleteBill,
  getAccounts,
  getApiErrorMessage,
  getBills,
  getCategories,
  payBill,
  updateBill,
} from '../api/client'
import type { Account, Bill, BillInput, Category } from '../api/types'
import { MAX_AMOUNT } from '../constants'
import { getDateGuardrails } from '../utils/dateGuardrails'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return dateFormatter.format(new Date(year, month - 1, day))
}

function getDaysUntilDue(dueDate: string): number {
  const due = new Date(dueDate)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  due.setHours(0, 0, 0, 0)
  return Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function getDueDateColor(daysUntilDue: number): 'error' | 'warning' | 'success' {
  if (daysUntilDue < 0) return 'error'
  if (daysUntilDue <= 7) return 'warning'
  return 'success'
}

function getDueDateLabel(daysUntilDue: number): string {
  if (daysUntilDue < 0) return `Atrasado ${Math.abs(daysUntilDue)} dias`
  if (daysUntilDue === 0) return 'Vence hoje'
  if (daysUntilDue === 1) return 'Vence amanhã'
  return `Vence em ${daysUntilDue} dias`
}

const emptyForm: BillInput = {
  account_id: null,
  category_id: null,
  description: '',
  amount: 0,
  due_date: new Date().toISOString().split('T')[0],
}

type TabValue = 'pending' | 'paid'

export default function Bills() {
  const [allBills, setAllBills] = useState<Bill[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [tabValue, setTabValue] = useState<TabValue>('pending')

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Bill | null>(null)
  const [form, setForm] = useState<BillInput>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [payDialogOpen, setPayDialogOpen] = useState(false)
  const [pendingPayBill, setPendingPayBill] = useState<Bill | null>(null)
  const [payAccountId, setPayAccountId] = useState<number | ''>('')
  const [payError, setPayError] = useState<string | null>(null)
  const [paying, setPaying] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<Bill | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [billsData, accountsData, categoriesData] = await Promise.all([
        getBills(),
        getAccounts(),
        getCategories(),
      ])
      setAllBills(billsData)
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

  const bills = allBills.filter((b) =>
    tabValue === 'pending' ? !b.paid : b.paid,
  )

  const openCreateForm = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (bill: Bill) => {
    setEditing(bill)
    setForm({
      account_id: bill.account_id,
      category_id: bill.category_id,
      description: bill.description,
      amount: bill.amount,
      due_date: bill.due_date,
    })
    setFormError(null)
    setFormOpen(true)
  }

  const dateGuardrails = getDateGuardrails()

  const handleSubmit = async () => {
    setFormError(null)
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

    setSubmitting(true)
    try {
      if (editing) {
        await updateBill(editing.id, form)
      } else {
        await createBill(form)
      }
      setFormOpen(false)
      await loadData()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const openPayDialog = (bill: Bill) => {
    setPendingPayBill(bill)
    setPayAccountId('')
    setPayError(null)
    setPayDialogOpen(true)
  }

  const handlePay = async () => {
    if (!pendingPayBill) return
    if (payAccountId === '') {
      setPayError('Selecione uma conta.')
      return
    }

    setPaying(true)
    setPayError(null)
    try {
      await payBill(pendingPayBill.id, { account_id: Number(payAccountId) })
      setPayDialogOpen(false)
      await loadData()
    } catch (err) {
      setPayError(getApiErrorMessage(err))
    } finally {
      setPaying(false)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteBill(pendingDelete.id)
      setPendingDelete(null)
      await loadData()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  const expenseCategories = categories.filter((c) => c.type === 'expense')

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Contas a Pagar
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <Card>
          <Tabs
            value={tabValue}
            onChange={(_, newValue) => setTabValue(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="Pendentes" value="pending" />
            <Tab label="Pagas" value="paid" />
          </Tabs>

          {loading ? (
            <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : bills.length === 0 ? (
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <ReceiptOutlinedIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">
                {tabValue === 'pending' ? 'Nenhuma conta pendente.' : 'Nenhuma conta paga.'}
              </Typography>
            </Box>
          ) : (
            <List disablePadding>
              {bills.map((bill, index) => {
                const daysUntilDue = getDaysUntilDue(bill.due_date)
                const category = categories.find((c) => c.id === bill.category_id)
                return (
                  <Box key={bill.id}>
                    {index > 0 && <Divider component="li" />}
                    <ListItem
                      sx={{ py: 1.5 }}
                      secondaryAction={
                        <Stack direction="row" spacing={0.5}>
                          {!bill.paid && (
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => openPayDialog(bill)}
                            >
                              Marcar como pago
                            </Button>
                          )}
                          <IconButton
                            aria-label="Editar"
                            size="small"
                            onClick={() => openEditForm(bill)}
                          >
                            <EditOutlinedIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            aria-label="Excluir"
                            size="small"
                            onClick={() => setPendingDelete(bill)}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      }
                    >
                      <ListItemText
                        primary={bill.description}
                        secondary={
                          <Stack spacing={0.5}>
                            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                              <Typography variant="caption" color="text.secondary">
                                {currencyFormatter.format(bill.amount)}
                              </Typography>
                              {!bill.paid && (
                                <Chip
                                  label={getDueDateLabel(daysUntilDue)}
                                  size="small"
                                  variant="outlined"
                                  color={getDueDateColor(daysUntilDue)}
                                  sx={{ height: 20, fontSize: 11 }}
                                />
                              )}
                              {bill.paid && (
                                <Chip
                                  label={`Pago em ${formatDate(bill.due_date)}`}
                                  size="small"
                                  variant="outlined"
                                  color="success"
                                  sx={{ height: 20, fontSize: 11 }}
                                />
                              )}
                            </Stack>
                            {category && (
                              <Typography
                                variant="caption"
                                sx={{
                                  display: 'inline-block',
                                  bgcolor: category.color,
                                  color: '#fff',
                                  px: 0.75,
                                  py: 0.25,
                                  borderRadius: 0.5,
                                  width: 'fit-content',
                                }}
                              >
                                {category.name}
                              </Typography>
                            )}
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
        aria-label="Adicionar conta"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editing ? 'Editar conta' : 'Nova conta'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              label="Descrição"
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
              fullWidth
              autoFocus={!editing}
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
              label="Data de vencimento"
              type="date"
              value={form.due_date}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, due_date: e.target.value }))
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
              {expenseCategories.map((category) => (
                <MenuItem key={category.id} value={category.id}>
                  {category.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Conta (opcional)"
              value={form.account_id || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  account_id: e.target.value ? Number(e.target.value) : null,
                }))
              }
              fullWidth
            >
              <MenuItem value="">— Sem conta —</MenuItem>
              {accounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name}
                </MenuItem>
              ))}
            </TextField>
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

      <Dialog open={payDialogOpen} onClose={() => setPayDialogOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Marcar como pago</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {payError && <Alert severity="error">{payError}</Alert>}
            <Typography variant="body2" color="text.secondary">
              Qual conta pagará esta conta?
            </Typography>
            <TextField
              select
              label="Conta"
              value={payAccountId}
              onChange={(e) => setPayAccountId(e.target.value === '' ? '' : Number(e.target.value))}
              fullWidth
              autoFocus
            >
              {accounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setPayDialogOpen(false)} disabled={paying}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handlePay} disabled={paying}>
            Marcar como pago
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)}>
        <DialogTitle>Excluir conta?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja excluir "{pendingDelete?.description}"? Essa ação não
            pode ser desfeita.
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
