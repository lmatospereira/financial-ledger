import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material'
import { changeMyPassword, getApiErrorMessage } from '../api/client'

interface ChangePasswordDialogProps {
  open: boolean
  onClose: () => void
}

const emptyForm = {
  current_password: '',
  new_password: '',
  confirm_password: '',
}

export default function ChangePasswordDialog({
  open,
  onClose,
}: ChangePasswordDialogProps) {
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(emptyForm)
      setError(null)
      setSuccess(false)
    }
  }, [open])

  const handleSubmit = async () => {
    setError(null)

    if (!form.current_password) {
      setError('Informe sua senha atual.')
      return
    }
    if (!form.new_password || form.new_password.length < 6) {
      setError('A nova senha deve ter pelo menos 6 caracteres.')
      return
    }
    if (form.new_password !== form.confirm_password) {
      setError('A confirmação não corresponde à nova senha.')
      return
    }

    setSubmitting(true)
    try {
      await changeMyPassword({
        current_password: form.current_password,
        new_password: form.new_password,
      })
      setSuccess(true)
      setForm(emptyForm)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Alterar senha</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          {success && (
            <Alert severity="success">Senha alterada com sucesso.</Alert>
          )}

          <TextField
            label="Senha atual"
            type="password"
            value={form.current_password}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, current_password: e.target.value }))
            }
            fullWidth
            autoFocus
            autoComplete="current-password"
          />
          <TextField
            label="Nova senha"
            type="password"
            value={form.new_password}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, new_password: e.target.value }))
            }
            fullWidth
            autoComplete="new-password"
          />
          <TextField
            label="Confirmar nova senha"
            type="password"
            value={form.confirm_password}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, confirm_password: e.target.value }))
            }
            fullWidth
            autoComplete="new-password"
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={submitting}>
          Fechar
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          Salvar
        </Button>
      </DialogActions>
    </Dialog>
  )
}
