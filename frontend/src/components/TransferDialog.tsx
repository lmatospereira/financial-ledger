import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from '@mui/material'
import { createTransfer, getApiErrorMessage } from '../api/client'
import type { Account } from '../api/types'

interface TransferDialogProps {
  open: boolean
  accounts: Account[]
  onClose: () => void
  onSuccess: () => Promise<void>
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

const emptyForm = {
  from_account_id: '' as number | '',
  to_account_id: '' as number | '',
  amount: '',
  date: todayIso(),
  description: '',
}

export default function TransferDialog({
  open,
  accounts,
  onClose,
  onSuccess,
}: TransferDialogProps) {
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(emptyForm)
      setError(null)
    }
  }, [open])

  const handleSubmit = async () => {
    setError(null)

    if (form.from_account_id === '' || form.to_account_id === '') {
      setError('Selecione a conta de origem e a conta de destino.')
      return
    }
    if (form.from_account_id === form.to_account_id) {
      setError('A conta de origem e a conta de destino devem ser diferentes.')
      return
    }
    const amountNumber = Number(form.amount.replace(',', '.'))
    if (!form.amount || Number.isNaN(amountNumber) || amountNumber <= 0) {
      setError('Informe um valor válido maior que zero.')
      return
    }
    if (!form.date) {
      setError('Informe a data.')
      return
    }

    setSubmitting(true)
    try {
      await createTransfer({
        from_account_id: form.from_account_id,
        to_account_id: form.to_account_id,
        amount: amountNumber,
        date: form.date,
        description: form.description.trim(),
      })
      await onSuccess()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Nova transferência</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            select
            label="Conta de origem"
            value={form.from_account_id}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                from_account_id: e.target.value === '' ? '' : Number(e.target.value),
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
            select
            label="Conta de destino"
            value={form.to_account_id}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                to_account_id: e.target.value === '' ? '' : Number(e.target.value),
              }))
            }
            fullWidth
          >
            {accounts
              .filter((account) => account.id !== form.from_account_id)
              .map((account) => (
                <MenuItem key={account.id} value={account.id}>
                  {account.name}
                </MenuItem>
              ))}
          </TextField>

          <Stack direction="row" spacing={2}>
            <TextField
              label="Valor"
              value={form.amount}
              onChange={(e) => setForm((prev) => ({ ...prev, amount: e.target.value }))}
              fullWidth
              inputMode="decimal"
              placeholder="0,00"
            />
            <TextField
              label="Data"
              type="date"
              value={form.date}
              onChange={(e) => setForm((prev) => ({ ...prev, date: e.target.value }))}
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Stack>

          <TextField
            label="Descrição"
            value={form.description}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, description: e.target.value }))
            }
            fullWidth
            placeholder="Opcional"
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={submitting}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          Transferir
        </Button>
      </DialogActions>
    </Dialog>
  )
}
