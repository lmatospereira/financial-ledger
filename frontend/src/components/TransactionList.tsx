import { useState } from 'react'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import RepeatIcon from '@mui/icons-material/Repeat'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useTheme,
} from '@mui/material'
import type { Account, Transaction } from '../api/types'
import { getApiErrorMessage } from '../api/client'

interface TransactionListProps {
  transactions: Transaction[]
  accounts: Account[]
  onEdit: (transaction: Transaction) => void
  onDelete: (transaction: Transaction) => Promise<void>
  onConfirm?: (transaction: Transaction, accountId: number) => Promise<void>
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

function formatDayHeader(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  const date = new Date(year, month - 1, day)

  const today = new Date()
  const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate())

  if (date.getTime() === todayDate.getTime()) {
    return 'Hoje'
  }

  const yesterday = new Date(todayDate)
  yesterday.setDate(yesterday.getDate() - 1)
  if (date.getTime() === yesterday.getTime()) {
    return 'Ontem'
  }

  const options: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    day: 'numeric',
  }

  // Include month if the year is different
  if (date.getFullYear() !== today.getFullYear()) {
    options.month = 'long'
  }

  const formatter = new Intl.DateTimeFormat('pt-BR', options)
  const formatted = formatter.format(date)

  // Capitalize the first letter (weekday is lowercased by pt-BR locale)
  return formatted.charAt(0).toUpperCase() + formatted.slice(1)
}

function groupTransactionsByDate(
  transactions: Transaction[],
): Array<{ date: string; transactions: Transaction[] }> {
  const groups: Record<string, Transaction[]> = {}

  for (const transaction of transactions) {
    if (!groups[transaction.date]) {
      groups[transaction.date] = []
    }
    groups[transaction.date].push(transaction)
  }

  // Return groups in order they appear (already sorted)
  return Object.entries(groups).map(([date, txns]) => ({
    date,
    transactions: txns,
  }))
}

function calculateDaySubtotal(transactions: Transaction[]): number {
  let income = 0
  let expense = 0

  for (const tx of transactions) {
    if (tx.type === 'transfer') continue
    if (tx.type === 'income') {
      income += tx.amount
    } else {
      expense += tx.amount
    }
  }

  return income - expense
}

export default function TransactionList({
  transactions,
  accounts,
  onEdit,
  onDelete,
  onConfirm,
}: TransactionListProps) {
  const theme = useTheme()
  const [pendingDelete, setPendingDelete] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState(false)

  const [pendingPay, setPendingPay] = useState<Transaction | null>(null)
  const [payAccountId, setPayAccountId] = useState<number | ''>('')
  const [payError, setPayError] = useState<string | null>(null)
  const [paying, setPaying] = useState(false)

  const sorted = [...transactions].sort((a, b) =>
    a.date === b.date ? b.id - a.id : a.date < b.date ? 1 : -1,
  )

  const groups = groupTransactionsByDate(sorted)

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await onDelete(pendingDelete)
      setPendingDelete(null)
    } finally {
      setDeleting(false)
    }
  }

  const openPayDialog = (transaction: Transaction) => {
    setPendingPay(transaction)
    setPayAccountId(transaction.account_id)
    setPayError(null)
  }

  const handlePay = async () => {
    if (!pendingPay || payAccountId === '' || !onConfirm) return
    setPaying(true)
    setPayError(null)
    try {
      await onConfirm(pendingPay, payAccountId)
      setPendingPay(null)
    } catch (err) {
      setPayError(getApiErrorMessage(err))
    } finally {
      setPaying(false)
    }
  }

  if (sorted.length === 0) {
    return (
      <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
        <ReceiptLongOutlinedIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
        <Typography variant="body1">
          Nenhum lançamento neste mês ainda.
        </Typography>
      </Box>
    )
  }

  return (
    <>
      <List disablePadding>
        {groups.map((group, groupIndex) => {
          const daySubtotal = calculateDaySubtotal(group.transactions)
          const subtotalColor =
            daySubtotal > 0
              ? 'success.main'
              : daySubtotal < 0
                ? 'error.main'
                : 'text.secondary'

          return (
            <Box key={group.date}>
              {/* Day header with subtotal */}
              <Box
                sx={{
                  position: 'sticky',
                  top: 0,
                  zIndex: 10,
                  px: 2,
                  py: 1,
                  backgroundColor: 'action.hover',
                  borderLeft: `4px solid ${theme.palette.primary.main}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {formatDayHeader(group.date)}
                </Typography>
                <Typography
                  variant="body2"
                  color={subtotalColor}
                  sx={{ fontWeight: 600 }}
                >
                  {daySubtotal > 0 ? '+ ' : daySubtotal < 0 ? '− ' : ''}
                  {currencyFormatter.format(Math.abs(daySubtotal))}
                </Typography>
              </Box>

              {/* Transactions for this day */}
              {group.transactions.map((transaction, transIndex) => {
                const isTransfer = transaction.type === 'transfer'
                return (
                  <Box key={transaction.id}>
                    {transIndex > 0 && <Divider component="li" />}
                    <ListItem
                      sx={{
                        py: 1.5,
                        ...(transaction.status === 'pending' && onConfirm
                          ? { cursor: 'pointer' }
                          : {}),
                      }}
                      onClick={
                        transaction.status === 'pending' && onConfirm
                          ? () => openPayDialog(transaction)
                          : undefined
                      }
                      secondaryAction={
                        <Stack direction="row" spacing={0.5}>
                          {/* Transfers aren't editable through TransactionForm
                              (it never submits type: 'transfer') — hide Edit so
                              users aren't offered a broken flow. */}
                          {!isTransfer && (
                            <IconButton
                              aria-label="Editar"
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation()
                                onEdit(transaction)
                              }}
                            >
                              <EditOutlinedIcon fontSize="small" />
                            </IconButton>
                          )}
                          <IconButton
                            aria-label="Excluir"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              setPendingDelete(transaction)
                            }}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Stack>
                      }
                    >
                      {isTransfer && (
                        <SwapHorizIcon
                          fontSize="small"
                          color="info"
                          sx={{ mr: 1, flexShrink: 0 }}
                        />
                      )}
                      {transaction.recurring_transaction_id && (
                        <Tooltip title="Gerado por regra recorrente">
                          <RepeatIcon
                            fontSize="small"
                            color="action"
                            sx={{ mr: 1, flexShrink: 0 }}
                          />
                        </Tooltip>
                      )}
                      {transaction.installment_number &&
                        transaction.installment_total && (
                          <Tooltip
                            title={`Parcela ${transaction.installment_number} de ${transaction.installment_total}`}
                          >
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 0.25,
                                mr: 1,
                                flexShrink: 0,
                              }}
                            >
                              <CreditCardIcon
                                fontSize="small"
                                color="action"
                              />
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{ fontSize: 11 }}
                              >
                                {transaction.installment_number}/
                                {transaction.installment_total}
                              </Typography>
                            </Box>
                          </Tooltip>
                        )}
                      <ListItemText
                        primary={transaction.description || 'Transferência'}
                        secondary={
                          isTransfer ? (
                            <Typography variant="caption" color="text.secondary">
                              {transaction.account?.name ?? 'Conta'} →{' '}
                              {transaction.to_account?.name ?? 'Conta'}
                            </Typography>
                          ) : (
                            <Stack spacing={0.5} direction="row" sx={{ mt: 0.5, alignItems: 'center', flexWrap: 'wrap' }}>
                              {transaction.status === 'pending' && (
                                <Chip
                                  size="small"
                                  label="Pendente"
                                  color="warning"
                                  sx={{
                                    height: 20,
                                    fontSize: 11,
                                  }}
                                />
                              )}
                              {transaction.category && (
                                <Chip
                                  size="small"
                                  label={transaction.category.name}
                                  sx={{
                                    bgcolor: transaction.category.color,
                                    color: 'white',
                                    height: 20,
                                    fontSize: 11,
                                  }}
                                />
                              )}
                            </Stack>
                          )
                        }
                      />
                      <Typography
                        variant="body1"
                        color={
                          isTransfer
                            ? 'info.main'
                            : transaction.type === 'income'
                              ? 'success.main'
                              : 'error.main'
                        }
                        sx={{
                          fontWeight: 600,
                          mr: 6,
                          whiteSpace: 'nowrap',
                          minWidth: 0,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {isTransfer ? '⇄ ' : transaction.type === 'income' ? '+ ' : '− '}
                        {currencyFormatter.format(transaction.amount)}
                      </Typography>
                    </ListItem>
                  </Box>
                )
              })}

              {/* Divider between day groups */}
              {groupIndex < groups.length - 1 && <Divider />}
            </Box>
          )
        })}
      </List>

      <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)}>
        <DialogTitle>Excluir lançamento?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja excluir “{pendingDelete?.description}”? Essa
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

      <Dialog open={Boolean(pendingPay)} onClose={() => setPendingPay(null)} fullWidth maxWidth="xs">
        <DialogTitle>Pagar lançamento</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {payError && <Alert severity="error">{payError}</Alert>}
            <Typography variant="body2" color="text.secondary">
              {pendingPay?.description} —{' '}
              {pendingPay && currencyFormatter.format(pendingPay.amount)}
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
          <Button onClick={() => setPendingPay(null)} disabled={paying}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handlePay} disabled={paying}>
            Pagar
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
