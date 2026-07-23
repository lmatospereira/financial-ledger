import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'
import type { Category, Transaction, TransactionInput } from '../api/types'

interface TransactionFormProps {
  open: boolean
  categories: Category[]
  initialValue: Transaction | null
  onClose: () => void
  onSubmit: (payload: TransactionInput) => Promise<void>
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

const emptyForm = {
  description: '',
  amount: '',
  type: 'expense' as 'income' | 'expense',
  date: todayIso(),
  category_id: '' as number | '',
}

export default function TransactionForm({
  open,
  categories,
  initialValue,
  onClose,
  onSubmit,
}: TransactionFormProps) {
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    if (initialValue) {
      setForm({
        description: initialValue.description,
        amount: String(initialValue.amount),
        type: initialValue.type,
        date: initialValue.date,
        category_id: initialValue.category_id ?? '',
      })
    } else {
      setForm(emptyForm)
    }
    setError(null)
  }, [open, initialValue])

  const filteredCategories = categories.filter((c) => c.type === form.type)

  const handleSubmit = async () => {
    setError(null)

    if (!form.description.trim()) {
      setError('Informe uma descrição.')
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
      await onSubmit({
        description: form.description.trim(),
        amount: amountNumber,
        type: form.type,
        date: form.date,
        category_id: form.category_id === '' ? null : Number(form.category_id),
      })
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Não foi possível salvar o lançamento.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {initialValue ? 'Editar lançamento' : 'Novo lançamento'}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <ToggleButtonGroup
            color="primary"
            exclusive
            fullWidth
            value={form.type}
            onChange={(_, value) => {
              if (value) {
                setForm((prev) => ({
                  ...prev,
                  type: value,
                  category_id: '',
                }))
              }
            }}
          >
            <ToggleButton value="income">Receita</ToggleButton>
            <ToggleButton value="expense">Despesa</ToggleButton>
          </ToggleButtonGroup>

          <TextField
            label="Descrição"
            value={form.description}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, description: e.target.value }))
            }
            fullWidth
            autoFocus
          />

          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              label="Valor"
              value={form.amount}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, amount: e.target.value }))
              }
              fullWidth
              inputMode="decimal"
              placeholder="0,00"
            />
            <TextField
              label="Data"
              type="date"
              value={form.date}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, date: e.target.value }))
              }
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Box>

          <TextField
            select
            label="Categoria"
            value={form.category_id}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                category_id: e.target.value === '' ? '' : Number(e.target.value),
              }))
            }
            fullWidth
          >
            <MenuItem value="">
              <em>Sem categoria</em>
            </MenuItem>
            {filteredCategories.map((category) => (
              <MenuItem key={category.id} value={category.id}>
                <Box
                  component="span"
                  sx={{
                    display: 'inline-block',
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    bgcolor: category.color,
                    mr: 1,
                    verticalAlign: 'middle',
                  }}
                />
                {category.name}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={submitting}>
          Cancelar
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          Salvar
        </Button>
      </DialogActions>
    </Dialog>
  )
}
