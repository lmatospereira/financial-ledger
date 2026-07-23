import { useState } from 'react'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import {
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
  Stack,
  Typography,
} from '@mui/material'
import type { Transaction } from '../api/types'

interface TransactionListProps {
  transactions: Transaction[]
  onEdit: (transaction: Transaction) => void
  onDelete: (transaction: Transaction) => Promise<void>
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: 'short',
})

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return dateFormatter.format(new Date(year, month - 1, day))
}

export default function TransactionList({
  transactions,
  onEdit,
  onDelete,
}: TransactionListProps) {
  const [pendingDelete, setPendingDelete] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState(false)

  const sorted = [...transactions].sort((a, b) =>
    a.date === b.date ? b.id - a.id : a.date < b.date ? 1 : -1,
  )

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
        {sorted.map((transaction, index) => {
          const isTransfer = transaction.type === 'transfer'
          return (
            <Box key={transaction.id}>
              {index > 0 && <Divider component="li" />}
              <ListItem
                sx={{ py: 1.5 }}
                secondaryAction={
                  <Stack direction="row" spacing={0.5}>
                    {/* Transfers aren't editable through TransactionForm
                        (it never submits type: 'transfer') — hide Edit so
                        users aren't offered a broken flow. */}
                    {!isTransfer && (
                      <IconButton
                        aria-label="Editar"
                        size="small"
                        onClick={() => onEdit(transaction)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                    )}
                    <IconButton
                      aria-label="Excluir"
                      size="small"
                      onClick={() => setPendingDelete(transaction)}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                }
              >
                <Box sx={{ width: 52, flexShrink: 0 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textTransform: 'capitalize' }}
                  >
                    {formatDate(transaction.date)}
                  </Typography>
                </Box>
                {isTransfer && (
                  <SwapHorizIcon
                    fontSize="small"
                    color="info"
                    sx={{ mr: 1, flexShrink: 0 }}
                  />
                )}
                <ListItemText
                  primary={transaction.description || 'Transferência'}
                  secondary={
                    isTransfer ? (
                      <Typography variant="caption" color="text.secondary">
                        {transaction.account?.name ?? 'Conta'} →{' '}
                        {transaction.to_account?.name ?? 'Conta'}
                      </Typography>
                    ) : transaction.category ? (
                      <Chip
                        size="small"
                        label={transaction.category.name}
                        sx={{
                          mt: 0.5,
                          bgcolor: transaction.category.color,
                          color: '#fff',
                          height: 20,
                          fontSize: 11,
                        }}
                      />
                    ) : undefined
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
                  sx={{ fontWeight: 600, mr: 6, whiteSpace: 'nowrap' }}
                >
                  {isTransfer ? '⇄ ' : transaction.type === 'income' ? '+ ' : '− '}
                  {currencyFormatter.format(transaction.amount)}
                </Typography>
              </ListItem>
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
    </>
  )
}
