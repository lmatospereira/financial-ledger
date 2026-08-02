import { useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import GroupOutlinedIcon from '@mui/icons-material/GroupOutlined'
import KeyOutlinedIcon from '@mui/icons-material/KeyOutlined'
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
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import {
  createUser,
  deleteUser,
  getApiErrorMessage,
  getUsers,
  resetUserPassword,
  updateUser,
} from '../api/client'
import { useAuth } from '../context/authContext'
import type { CurrentUser } from '../api/types'

interface UserFormState {
  username: string
  name: string
  password: string
  is_admin: boolean
}

const emptyForm: UserFormState = {
  username: '',
  name: '',
  password: '',
  is_admin: false,
}

export default function Users() {
  const { currentUser } = useAuth()

  const [users, setUsers] = useState<CurrentUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<CurrentUser | null>(null)
  const [form, setForm] = useState<UserFormState>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<CurrentUser | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const [resetPasswordOpen, setResetPasswordOpen] = useState(false)
  const [pendingPasswordReset, setPendingPasswordReset] = useState<CurrentUser | null>(null)
  const [resetPasswordForm, setResetPasswordForm] = useState<string>('')
  const [resetPasswordError, setResetPasswordError] = useState<string | null>(null)
  const [resettingPassword, setResettingPassword] = useState(false)

  const loadUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getUsers()
      setUsers(data)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const openCreateForm = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (user: CurrentUser) => {
    setEditing(user)
    setForm({ username: user.username, name: user.name, password: '', is_admin: user.is_admin })
    setFormError(null)
    setFormOpen(true)
  }

  const handleSubmit = async () => {
    setFormError(null)
    if (!form.username.trim()) {
      setFormError('Informe um nome de usuário.')
      return
    }
    if (!form.name.trim()) {
      setFormError('Informe o nome.')
      return
    }
    if (!editing && form.password.length < 8) {
      setFormError('A senha deve ter pelo menos 8 caracteres.')
      return
    }

    setSubmitting(true)
    try {
      if (editing) {
        await updateUser(editing.id, {
          // Backend always lowercases the username, but normalize it here
          // too so the UI reflects the actual stored value immediately.
          username: form.username.trim().toLowerCase(),
          name: form.name.trim(),
          is_admin: form.is_admin,
        })
      } else {
        await createUser({
          username: form.username.trim().toLowerCase(),
          name: form.name.trim(),
          password: form.password,
          is_admin: form.is_admin,
        })
      }
      setFormOpen(false)
      await loadUsers()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const openDeleteConfirm = (user: CurrentUser) => {
    setDeleteError(null)
    setPendingDelete(user)
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleteError(null)
    setDeleting(true)
    try {
      await deleteUser(pendingDelete.id)
      setPendingDelete(null)
      await loadUsers()
    } catch (err) {
      setDeleteError(getApiErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  const openPasswordResetDialog = (user: CurrentUser) => {
    setPendingPasswordReset(user)
    setResetPasswordForm('')
    setResetPasswordError(null)
    setResetPasswordOpen(true)
  }

  const handlePasswordResetSubmit = async () => {
    setResetPasswordError(null)
    if (!pendingPasswordReset) return
    if (resetPasswordForm.length < 8) {
      setResetPasswordError('A senha deve ter pelo menos 8 caracteres.')
      return
    }
    setResettingPassword(true)
    try {
      await resetUserPassword(pendingPasswordReset.id, resetPasswordForm)
      setResetPasswordOpen(false)
      setPendingPasswordReset(null)
      await loadUsers()
    } catch (err) {
      setResetPasswordError(getApiErrorMessage(err))
    } finally {
      setResettingPassword(false)
    }
  }

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Usuários
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <Card>
          {loading ? (
            <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : users.length === 0 ? (
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <GroupOutlinedIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">Nenhum usuário cadastrado.</Typography>
            </Box>
          ) : (
            <List disablePadding>
              {users.map((user, index) => (
                <Box key={user.id}>
                  {index > 0 && <Divider component="li" />}
                  <ListItem
                    sx={{ py: 1.5 }}
                    secondaryAction={
                      <Stack direction="row" spacing={0.5}>
                        <IconButton
                          aria-label="Editar"
                          size="small"
                          onClick={() => openEditForm(user)}
                        >
                          <EditOutlinedIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          aria-label="Redefinir senha"
                          size="small"
                          onClick={() => openPasswordResetDialog(user)}
                        >
                          <KeyOutlinedIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          aria-label="Excluir"
                          size="small"
                          onClick={() => openDeleteConfirm(user)}
                          disabled={user.id === currentUser?.id}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    }
                  >
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                          <span>{user.name}</span>
                          <Typography variant="body2" color="text.secondary">
                            @{user.username}
                          </Typography>
                          {user.id === currentUser?.id && (
                            <Chip label="Você" size="small" variant="outlined" />
                          )}
                        </Stack>
                      }
                      secondary={user.is_admin ? 'Administrador' : 'Usuário'}
                    />
                  </ListItem>
                </Box>
              ))}
            </List>
          )}
        </Card>
      </Stack>

      <Fab
        color="primary"
        aria-label="Adicionar usuário"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editing ? 'Editar usuário' : 'Novo usuário'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              label="Nome"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              fullWidth
              autoFocus
              autoComplete="name"
            />

            <TextField
              label="Usuário"
              value={form.username}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, username: e.target.value }))
              }
              fullWidth
              autoComplete="username"
              helperText="Sempre salvo em minúsculo, sem espaços"
            />

            {!editing && (
              <TextField
                label="Senha"
                type="password"
                value={form.password}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, password: e.target.value }))
                }
                fullWidth
                autoComplete="new-password"
              />
            )}

            <FormControlLabel
              control={
                <Switch
                  checked={form.is_admin}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, is_admin: e.target.checked }))
                  }
                  disabled={editing?.id === currentUser?.id}
                />
              }
              label="Administrador"
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
        <DialogTitle>Excluir usuário?</DialogTitle>
        <DialogContent>
          {deleteError ? (
            <Alert severity="error">{deleteError}</Alert>
          ) : (
            <DialogContentText>
              Tem certeza que deseja excluir "{pendingDelete?.name}" (@{pendingDelete?.username})?
              Essa ação não pode ser desfeita.
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

      <Dialog open={resetPasswordOpen} onClose={() => setResetPasswordOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Redefinir senha</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {resetPasswordError && <Alert severity="error">{resetPasswordError}</Alert>}

            <TextField
              label="Nova senha"
              type="password"
              value={resetPasswordForm}
              onChange={(e) => setResetPasswordForm(e.target.value)}
              fullWidth
              autoFocus
              autoComplete="new-password"
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setResetPasswordOpen(false)} disabled={resettingPassword}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handlePasswordResetSubmit} disabled={resettingPassword}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </Layout>
  )
}
