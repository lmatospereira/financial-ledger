import { useEffect, useState } from 'react'
import CreditCardIcon from '@mui/icons-material/CreditCard'
import {
  Alert,
  Box,
  Card,
  CircularProgress,
  Divider,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import MonthSelector from '../components/MonthSelector'
import {
  getAccounts,
  getCreditCardInvoice,
  getApiErrorMessage,
} from '../api/client'
import type { Account, CreditCardInvoice } from '../api/types'

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

// Compute luminance to determine if white or black text should be used
function getContrastColor(hexColor: string): string {
  const hex = hexColor.replace('#', '')
  const r = parseInt(hex.substring(0, 2), 16)
  const g = parseInt(hex.substring(2, 4), 16)
  const b = parseInt(hex.substring(4, 6), 16)

  // Luminance formula from WCAG
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

  return luminance > 0.5 ? '#000000' : '#FFFFFF'
}

export default function CreditCards() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedCardIndex, setSelectedCardIndex] = useState(0)
  const [month, setMonth] = useState<number>(() => new Date().getMonth() + 1)
  const [year, setYear] = useState<number>(() => new Date().getFullYear())

  const [invoice, setInvoice] = useState<CreditCardInvoice | null>(null)
  const [invoiceLoading, setInvoiceLoading] = useState(false)
  const [invoiceError, setInvoiceError] = useState<string | null>(null)

  const creditCards = accounts.filter((acc) => acc.type === 'credit_card')
  const selectedCard = creditCards[selectedCardIndex] || null

  const loadAccounts = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAccounts()
      setAccounts(data)
      setSelectedCardIndex(0)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  useEffect(() => {
    const loadInvoice = async () => {
      if (!selectedCard) return

      setInvoiceLoading(true)
      setInvoiceError(null)
      try {
        const data = await getCreditCardInvoice(selectedCard.id, month, year)
        setInvoice(data)
      } catch (err) {
        setInvoiceError(getApiErrorMessage(err))
        setInvoice(null)
      } finally {
        setInvoiceLoading(false)
      }
    }

    loadInvoice()
  }, [selectedCard, month, year])

  if (loading) {
    return (
      <Layout>
        <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      </Layout>
    )
  }

  if (creditCards.length === 0) {
    return (
      <Layout>
        <Stack spacing={3}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Cartões de Crédito
          </Typography>

          {error && <Alert severity="error">{error}</Alert>}

          <Card>
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <CreditCardIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">
                Nenhum cartão de crédito cadastrado.
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Crie uma conta do tipo "Cartão de Crédito" em Contas para começar.
              </Typography>
            </Box>
          </Card>
        </Stack>
      </Layout>
    )
  }

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Cartões de Crédito
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        {creditCards.length > 1 && (
          <Tabs
            value={selectedCardIndex}
            onChange={(_, newValue) => setSelectedCardIndex(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            {creditCards.map((card) => (
              <Tab key={card.id} label={card.name} />
            ))}
          </Tabs>
        )}

        {selectedCard && (
          <>
            {/* Card Visual */}
            <Box
              sx={{
                bgcolor: selectedCard.color,
                color: getContrastColor(selectedCard.color),
                borderRadius: '20px',
                p: 3,
                minHeight: 200,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                boxShadow: 2,
              }}
            >
              <Box>
                <Typography
                  variant="body2"
                  sx={{
                    opacity: 0.8,
                    fontWeight: 600,
                    mb: 2,
                    textTransform: 'uppercase',
                    fontSize: '0.75rem',
                    letterSpacing: '0.5px',
                  }}
                >
                  Fatura
                </Typography>
                <Typography
                  variant="h3"
                  sx={{
                    fontWeight: 800,
                    lineHeight: 1.1,
                  }}
                >
                  {currencyFormatter.format(invoice?.total || 0)}
                </Typography>
              </Box>

              <Box>
                {invoice?.due_date && (
                  <Typography
                    variant="body2"
                    sx={{
                      opacity: 0.8,
                      fontWeight: 600,
                    }}
                  >
                    Vencimento: {formatDate(invoice.due_date)}
                  </Typography>
                )}
                <Typography
                  variant="body2"
                  sx={{
                    opacity: 0.8,
                    fontWeight: 600,
                    mt: 1,
                  }}
                >
                  {selectedCard.name}
                </Typography>
              </Box>
            </Box>

            {/* Month Selector */}
            <Card sx={{ p: 2 }}>
              <MonthSelector
                month={month}
                year={year}
                onChange={(m, y) => {
                  setMonth(m)
                  setYear(y)
                }}
              />
            </Card>

            {/* Invoice Details */}
            {invoiceError && <Alert severity="error">{invoiceError}</Alert>}

            {invoiceLoading ? (
              <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
              </Box>
            ) : invoice && invoice.transactions.length === 0 ? (
              <Card>
                <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
                  <CreditCardIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
                  <Typography variant="body1">
                    Nenhuma compra nesta fatura.
                  </Typography>
                </Box>
              </Card>
            ) : (
              <Card sx={{ p: 2 }}>
                <Stack spacing={1}>
                  {invoice?.transactions.map((transaction, index) => (
                    <Box key={transaction.id}>
                      {index > 0 && <Divider />}
                      <Box
                        sx={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          py: 1.5,
                        }}
                      >
                        <Box sx={{ flex: 1 }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 600,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {transaction.description}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ mt: 0.25, display: 'block' }}
                          >
                            {formatDate(transaction.date)}
                          </Typography>
                        </Box>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            ml: 2,
                            whiteSpace: 'nowrap',
                            color:
                              transaction.type === 'income'
                                ? 'success.main'
                                : 'error.main',
                          }}
                        >
                          {transaction.type === 'income' ? '+ ' : '− '}
                          {currencyFormatter.format(transaction.amount)}
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </Stack>
              </Card>
            )}
          </>
        )}
      </Stack>
    </Layout>
  )
}
