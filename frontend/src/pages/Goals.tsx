import { useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
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
  Fab,
  Grid,
  IconButton,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import ColorPicker from '../components/ColorPicker'
import {
  createGoal,
  deleteGoal,
  getAccounts,
  getApiErrorMessage,
  getGoals,
  updateGoal,
} from '../api/client'
import type { Account, Goal, GoalInput } from '../api/types'
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

function getDaysUntilDate(dateStr: string): number {
  const date = new Date(dateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  date.setHours(0, 0, 0, 0)
  return Math.ceil((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

const emptyForm: GoalInput = {
  name: '',
  target_amount: 0,
  account_id: 0,
  target_date: null,
  color: '#820AD1',
}

export default function Goals() {
  const [allGoals, setAllGoals] = useState<Goal[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Goal | null>(null)
  const [form, setForm] = useState<GoalInput>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<Goal | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [goalsData, accountsData] = await Promise.all([
        getGoals(),
        getAccounts(),
      ])
      setAllGoals(goalsData)
      setAccounts(accountsData)
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
    setForm({
      ...emptyForm,
      account_id: accounts.length > 0 ? accounts[0].id : 0,
    })
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (goal: Goal) => {
    setEditing(goal)
    setForm({
      name: goal.name,
      target_amount: goal.target_amount,
      account_id: goal.account?.id || 0,
      target_date: goal.target_date,
      color: goal.color,
    })
    setFormError(null)
    setFormOpen(true)
  }

  const dateGuardrails = getDateGuardrails()

  const handleSubmit = async () => {
    setFormError(null)
    if (!form.name.trim()) {
      setFormError('Informe um nome para a meta.')
      return
    }
    if (form.target_amount <= 0) {
      setFormError('Informe um valor maior que zero.')
      return
    }
    if (form.target_amount > MAX_AMOUNT) {
      setFormError(`Informe um valor menor que ${MAX_AMOUNT.toLocaleString('pt-BR')}.`)
      return
    }
    if (!form.account_id || form.account_id === 0) {
      setFormError('Selecione uma conta.')
      return
    }

    setSubmitting(true)
    try {
      if (editing) {
        await updateGoal(editing.id, form)
      } else {
        await createGoal(form)
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
      await deleteGoal(pendingDelete.id)
      setPendingDelete(null)
      await loadData()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Metas
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        {loading ? (
          <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : allGoals.length === 0 ? (
          <Card>
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <TrendingUpIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">
                Nenhuma meta criada. Comece criando uma!
              </Typography>
            </Box>
          </Card>
        ) : (
          <Grid container spacing={2}>
            {allGoals.map((goal) => (
              <Grid key={goal.id} size={{ xs: 12, sm: 6 }}>
                <Card
                  sx={{
                    p: 2,
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 1.5,
                  }}
                >
                  <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                        {goal.name}
                      </Typography>
                      {goal.account && (
                        <Chip
                          label={goal.account.name}
                          size="small"
                          sx={{
                            bgcolor: goal.account.color,
                            color: 'white',
                            height: 24,
                            fontSize: 11,
                          }}
                        />
                      )}
                    </Box>
                    <Stack direction="row" spacing={0.5}>
                      <IconButton
                        aria-label="Editar"
                        size="small"
                        onClick={() => openEditForm(goal)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        aria-label="Excluir"
                        size="small"
                        onClick={() => setPendingDelete(goal)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  </Stack>

                  <Box>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 0.5 }}>
                      <Typography variant="body2" color="text.secondary">
                        Progresso
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {Math.round(goal.progress_percent * 100)}%
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(goal.progress_percent * 100, 100)}
                      sx={{
                        height: 8,
                        borderRadius: 1,
                        backgroundColor: 'rgba(0,0,0,0.08)',
                      }}
                    />
                  </Box>

                  <Stack spacing={0.5}>
                    <Typography variant="caption" color="text.secondary">
                      {currencyFormatter.format(goal.current_amount)} de{' '}
                      {currencyFormatter.format(goal.target_amount)}
                    </Typography>
                    {goal.target_date && (
                      <Typography variant="caption" color="text.secondary">
                        Prazo: {formatDate(goal.target_date)}
                        {getDaysUntilDate(goal.target_date) < 0 && (
                          <Box
                            component="span"
                            sx={{
                              display: 'inline-block',
                              ml: 1,
                              px: 1,
                              py: 0.25,
                              bgcolor: 'error.light',
                              color: 'error.dark',
                              borderRadius: 0.5,
                              fontSize: 10,
                              fontWeight: 600,
                            }}
                          >
                            Vencida
                          </Box>
                        )}
                      </Typography>
                    )}
                  </Stack>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Stack>

      <Fab
        color="primary"
        aria-label="Adicionar meta"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editing ? 'Editar meta' : 'Nova meta'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              label="Nome da meta"
              value={form.name}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, name: e.target.value }))
              }
              fullWidth
              autoFocus={!editing}
            />

            <TextField
              label="Valor alvo"
              inputMode="decimal"
              placeholder="0,00"
              value={form.target_amount || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, target_amount: Number(e.target.value) }))
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
              select
              label="Conta"
              value={form.account_id || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  account_id: Number(e.target.value),
                }))
              }
              fullWidth
            >
              {accounts.map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Data alvo (opcional)"
              type="date"
              value={form.target_date || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  target_date: e.target.value || null,
                }))
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

            <ColorPicker
              value={form.color}
              onChange={(color) =>
                setForm((prev) => ({ ...prev, color }))
              }
              label="Cor da meta"
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
        <DialogTitle>Excluir meta?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja excluir "{pendingDelete?.name}"? Essa ação não
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
