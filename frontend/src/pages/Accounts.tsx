import { useEffect, useState } from 'react'
import axios from 'axios'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import WalletIcon from '@mui/icons-material/Wallet'
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
  Grid,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { ACCOUNT_TYPE_ICONS, ACCOUNT_TYPE_LABELS, ACCOUNT_TYPE_OPTIONS } from '../components/accountTypes'
import ColorPicker from '../components/ColorPicker'
import { PRESET_COLORS } from '../components/colors'
import Layout from '../components/Layout'
import TransferDialog from '../components/TransferDialog'
import {
  createAccount,
  deleteAccount,
  getAccounts,
  getApiErrorMessage,
  updateAccount,
} from '../api/client'
import type { Account, AccountInput } from '../api/types'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const emptyForm: AccountInput = {
  name: '',
  type: 'checking',
  color: PRESET_COLORS[4],
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)
  const [form, setForm] = useState<AccountInput>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<Account | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const [transferOpen, setTransferOpen] = useState(false)

  const loadAccounts = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAccounts()
      setAccounts(data)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  const openCreateForm = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (account: Account) => {
    setEditing(account)
    setForm({ name: account.name, type: account.type, color: account.color })
    setFormError(null)
    setFormOpen(true)
  }

  const handleSubmit = async () => {
    setFormError(null)
    if (!form.name.trim()) {
      setFormError('Informe um nome para a conta.')
      return
    }

    setSubmitting(true)
    try {
      if (editing) {
        await updateAccount(editing.id, form)
      } else {
        await createAccount(form)
      }
      setFormOpen(false)
      await loadAccounts()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const openDeleteConfirm = (account: Account) => {
    setDeleteError(null)
    setPendingDelete(account)
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleteError(null)
    setDeleting(true)
    try {
      await deleteAccount(pendingDelete.id)
      setPendingDelete(null)
      await loadAccounts()
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setDeleteError(
          'Esta conta possui lançamentos vinculados. Exclua ou reatribua os ' +
            'lançamentos dessa conta antes de excluí-la.',
        )
      } else {
        setDeleteError(getApiErrorMessage(err))
      }
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Layout>
      <Stack spacing={3}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
        >
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Contas
          </Typography>
          <Button
            variant="outlined"
            startIcon={<SwapHorizIcon />}
            onClick={() => setTransferOpen(true)}
            disabled={accounts.length < 2}
          >
            Nova transferência
          </Button>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        {loading ? (
          <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : accounts.length === 0 ? (
          <Card>
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <WalletIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">Nenhuma conta cadastrada.</Typography>
            </Box>
          </Card>
        ) : (
          <Grid container spacing={2}>
            {accounts.map((account) => {
              const TypeIcon = ACCOUNT_TYPE_ICONS[account.type]
              return (
                <Grid key={account.id} size={{ xs: 12, sm: 6, md: 4 }}>
                  <Card sx={{ height: '100%' }}>
                    <Box sx={{ p: 2.5 }}>
                      <Stack
                        direction="row"
                        spacing={1.5}
                        sx={{ alignItems: 'flex-start', mb: 2 }}
                      >
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 40,
                            height: 40,
                            borderRadius: '50%',
                            bgcolor: account.color,
                            color: 'white',
                            flexShrink: 0,
                          }}
                        >
                          <TypeIcon fontSize="small" />
                        </Box>
                        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600 }} noWrap>
                            {account.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {ACCOUNT_TYPE_LABELS[account.type]}
                          </Typography>
                        </Box>
                        <Stack direction="row" spacing={0.5}>
                          <IconButton
                            aria-label="Editar"
                            size="small"
                            onClick={() => openEditForm(account)}
                          >
                            <EditOutlinedIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            aria-label="Excluir"
                            size="small"
                            onClick={() => openDeleteConfirm(account)}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        Saldo
                      </Typography>
                      <Typography
                        variant="h6"
                        color={account.balance >= 0 ? 'success.main' : 'error.main'}
                        sx={{ fontWeight: 700 }}
                      >
                        {currencyFormatter.format(account.balance)}
                      </Typography>
                    </Box>
                  </Card>
                </Grid>
              )
            })}
          </Grid>
        )}
      </Stack>

      <Box
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
        }}
      >
        <IconButton
          aria-label="Adicionar conta"
          onClick={openCreateForm}
          sx={{
            width: 56,
            height: 56,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            boxShadow: 3,
            '&:hover': { bgcolor: 'primary.dark' },
          }}
        >
          <AddIcon />
        </IconButton>
      </Box>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editing ? 'Editar conta' : 'Nova conta'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              label="Nome"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              fullWidth
              autoFocus
            />

            <TextField
              select
              label="Tipo"
              value={form.type}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  type: e.target.value as AccountInput['type'],
                }))
              }
              fullWidth
            >
              {ACCOUNT_TYPE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>

            <ColorPicker
              value={form.color}
              onChange={(color) => setForm((prev) => ({ ...prev, color }))}
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
        <DialogTitle>Excluir conta?</DialogTitle>
        <DialogContent>
          {deleteError ? (
            <Alert severity="error">{deleteError}</Alert>
          ) : (
            <DialogContentText>
              Tem certeza que deseja excluir “{pendingDelete?.name}”? Essa ação não
              pode ser desfeita.
            </DialogContentText>
          )}
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

      <TransferDialog
        open={transferOpen}
        accounts={accounts}
        onClose={() => setTransferOpen(false)}
        onSuccess={async () => {
          setTransferOpen(false)
          await loadAccounts()
        }}
      />
    </Layout>
  )
}
