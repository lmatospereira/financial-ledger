import { useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'
import type { Account, Category, Transaction, TransactionInput } from '../api/types'
import { createInstallmentTransaction } from '../api/client'
import { MAX_AMOUNT } from '../constants'
import { getDateGuardrails } from '../utils/dateGuardrails'

interface TransactionFormProps {
  open: boolean
  categories: Category[]
  accounts: Account[]
  initialValue: Transaction | null
  defaultAccountId?: number | null
  onClose: () => void
  onSubmit: (payload: TransactionInput) => Promise<void>
  onInstallmentSuccess: () => Promise<void>
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function buildEmptyForm(defaultAccountId?: number | null) {
  return {
    description: '',
    amount: '',
    type: 'expense' as 'income' | 'expense',
    date: todayIso(),
    category_id: '' as number | '',
    account_id: (defaultAccountId ?? '') as number | '',
    isInstallment: false,
    installments: '',
    isPending: false,
  }
}

export default function TransactionForm({
  open,
  categories,
  accounts,
  initialValue,
  defaultAccountId,
  onClose,
  onSubmit,
  onInstallmentSuccess,
}: TransactionFormProps) {
  const [form, setForm] = useState(() => buildEmptyForm(defaultAccountId))
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const dateGuardrails = getDateGuardrails()

  useEffect(() => {
    if (!open) return
    if (initialValue) {
      setForm({
        description: initialValue.description,
        amount: String(initialValue.amount),
        // Transfers are never edited through this form (see contract), but
        // guard defensively in case a transfer row ever reaches here.
        type: initialValue.type === 'income' ? 'income' : 'expense',
        date: initialValue.date,
        category_id: initialValue.category_id ?? '',
        account_id: initialValue.account_id,
        isInstallment: false,
        installments: '',
        isPending: initialValue.status === 'pending',
      })
    } else {
      setForm(
        buildEmptyForm(
          defaultAccountId ?? (accounts.length === 1 ? accounts[0].id : null),
        ),
      )
    }
    setError(null)
  }, [open, initialValue, defaultAccountId, accounts])

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
    if (amountNumber > MAX_AMOUNT) {
      setError(`Informe um valor menor que ${MAX_AMOUNT.toLocaleString('pt-BR')}.`)
      return
    }
    if (!form.date) {
      setError('Informe a data.')
      return
    }
    if (form.account_id === '') {
      setError('Selecione a conta.')
      return
    }

    if (form.isInstallment) {
      if (!form.installments || Number(form.installments) < 1 || Number(form.installments) > 420) {
        setError('Número de parcelas deve estar entre 1 e 420.')
        return
      }

      setSubmitting(true)
      try {
        await createInstallmentTransaction({
          account_id: form.account_id,
          category_id: form.category_id === '' ? null : Number(form.category_id),
          description: form.description.trim(),
          total_amount: amountNumber,
          installments: Number(form.installments),
          type: form.type,
          first_date: form.date,
        })
        // The backend already created every installment transaction with its
        // split amount -- just close the dialog and let the parent refresh.
        // Do NOT call onSubmit here: it creates a real transaction, and doing
        // so with the full amountNumber duplicated the total on the start
        // date on top of the already-split installments.
        await onInstallmentSuccess()
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Não foi possível criar as parcelas.',
        )
      } finally {
        setSubmitting(false)
      }
    } else {
      setSubmitting(true)
      try {
        await onSubmit({
          description: form.description.trim(),
          amount: amountNumber,
          type: form.type,
          date: form.date,
          category_id: form.category_id === '' ? null : Number(form.category_id),
          account_id: form.account_id,
          status: form.isPending ? 'pending' : 'confirmed',
        })
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Não foi possível salvar o lançamento.',
        )
      } finally {
        setSubmitting(false)
      }
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
              label={form.isInstallment ? 'Valor total' : 'Valor'}
              value={form.amount}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, amount: e.target.value }))
              }
              fullWidth
              inputMode="decimal"
              placeholder="0,00"
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
              label="Data"
              type="date"
              value={form.date}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, date: e.target.value }))
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
          </Box>

          <TextField
            select
            label="Conta"
            value={form.account_id}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                account_id: e.target.value === '' ? '' : Number(e.target.value),
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

          {form.type === 'expense' && (
            <>
              <FormControlLabel
                control={
                  <input
                    type="checkbox"
                    checked={form.isInstallment}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        isInstallment: e.target.checked,
                        installments: e.target.checked ? '' : '',
                      }))
                    }
                  />
                }
                label="Compra parcelada"
              />

              {form.isInstallment && (
                <TextField
                  label="Número de parcelas"
                  type="number"
                  value={form.installments}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, installments: e.target.value }))
                  }
                  fullWidth
                  slotProps={{
                    input: {
                      inputProps: {
                        min: 1,
                        max: 420,
                      },
                    },
                  }}
                  placeholder="1"
                />
              )}
            </>
          )}

          <FormControlLabel
            control={
              <input
                type="checkbox"
                checked={form.isPending}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    isPending: e.target.checked,
                  }))
                }
              />
            }
            label="Marcar como pendente"
          />
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
