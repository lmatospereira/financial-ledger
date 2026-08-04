import { useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Fab,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import {
  createAsset,
  createInvestmentMovement,
  deleteInvestmentMovement,
  getApiErrorMessage,
  getAssets,
  getInvestmentMovements,
  updateInvestmentMovement,
} from '../api/client'
import type {
  Asset,
  AssetType,
  InvestmentMovement,
  InvestmentMovementInput,
  MovementType,
} from '../api/types'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

const assetTypeLabels: Record<AssetType, string> = {
  acao: 'Ação',
  fii: 'FII',
  etf: 'ETF',
  bdr: 'BDR',
  tesouro: 'Tesouro Direto',
  renda_fixa: 'Renda Fixa',
  outro: 'Outro',
}

const movementTypeLabels: Record<string, string> = {
  compra: 'Compra',
  venda: 'Venda',
  bonificacao: 'Bonificação',
  provento: 'Provento',
  desdobramento: 'Desdobramento',
  outro: 'Outro',
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number)
  return dateFormatter.format(new Date(year, month - 1, day))
}

const emptyMovementForm: InvestmentMovementInput = {
  asset_id: 0,
  date: new Date().toISOString().split('T')[0],
  movement_type: 'compra',
  quantity: 0,
  unit_price: null,
  total_value: 0,
}

export default function InvestmentMovements() {
  const [movements, setMovements] = useState<InvestmentMovement[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [filterAssetId, setFilterAssetId] = useState<number | ''>('')
  const [filterMovementType, setFilterMovementType] = useState<string>('')
  const [filterDateFrom, setFilterDateFrom] = useState<string>('')
  const [filterDateTo, setFilterDateTo] = useState<string>('')

  // Manual movement form dialog
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<InvestmentMovementInput>(emptyMovementForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [newTicker, setNewTicker] = useState<string>('')
  const [newAssetType, setNewAssetType] = useState<AssetType>('acao')
  const [editingMovement, setEditingMovement] = useState<InvestmentMovement | null>(null)

  // Delete movement dialog
  const [pendingDeleteMovement, setPendingDeleteMovement] = useState<InvestmentMovement | null>(null)
  const [deletingMovement, setDeletingMovement] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [movementsData, assetsData] = await Promise.all([
        getInvestmentMovements(),
        getAssets(),
      ])
      setMovements(movementsData)
      setAssets(assetsData)
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
    setEditingMovement(null)
    setForm(emptyMovementForm)
    setNewTicker('')
    setNewAssetType('acao')
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (movement: InvestmentMovement) => {
    const asset = assets.find((a) => a.id === movement.asset_id)
    setEditingMovement(movement)
    setForm({
      asset_id: movement.asset_id,
      date: movement.date,
      movement_type: movement.movement_type,
      quantity: movement.quantity,
      unit_price: movement.unit_price,
      total_value: movement.total_value,
    })
    setNewTicker(asset?.ticker || '')
    setNewAssetType(asset?.asset_type || 'acao')
    setFormError(null)
    setFormOpen(true)
  }

  const handleSubmitMovement = async () => {
    setFormError(null)

    if (form.quantity <= 0) {
      setFormError('Informe uma quantidade maior que zero.')
      return
    }

    if (form.total_value <= 0) {
      setFormError('Informe um valor total maior que zero.')
      return
    }

    const ticker = newTicker.trim().toUpperCase()
    if (!ticker) {
      setFormError('Informe um ticker.')
      return
    }

    setSubmitting(true)
    try {
      if (editingMovement) {
        // Editing existing movement
        await updateInvestmentMovement(editingMovement.id, form)
      } else {
        // Creating new movement
        let assetId = assets.find((a) => a.ticker === ticker)?.id
        if (!assetId) {
          const newAsset = await createAsset({
            ticker,
            name: null,
            asset_type: newAssetType,
            current_price: null,
          })
          assetId = newAsset.id
          setAssets((prev) => [...prev, newAsset])
        }
        await createInvestmentMovement({
          ...form,
          asset_id: assetId,
        })
      }
      setFormOpen(false)
      await loadData()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const confirmDeleteMovement = async () => {
    if (!pendingDeleteMovement) return
    setDeletingMovement(true)
    try {
      await deleteInvestmentMovement(pendingDeleteMovement.id)
      setPendingDeleteMovement(null)
      await loadData()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setDeletingMovement(false)
    }
  }

  // Filter movements
  const filteredMovements = movements.filter((movement) => {
    if (filterAssetId && movement.asset_id !== filterAssetId) return false
    if (filterMovementType && movement.movement_type !== filterMovementType) return false
    if (filterDateFrom && movement.date < filterDateFrom) return false
    if (filterDateTo && movement.date > filterDateTo) return false
    return true
  })

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Movimentações de Investimentos
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        {loading ? (
          <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* Filters Card */}
            <Card>
              <CardContent>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                  Filtros
                </Typography>
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                    <TextField
                      select
                      label="Ativo"
                      value={filterAssetId}
                      onChange={(e) => setFilterAssetId(e.target.value ? Number(e.target.value) : '')}
                      fullWidth
                      size="small"
                    >
                      <MenuItem value="">— Todos —</MenuItem>
                      {assets.map((asset) => (
                        <MenuItem key={asset.id} value={asset.id}>
                          {asset.ticker}
                        </MenuItem>
                      ))}
                    </TextField>

                    <TextField
                      select
                      label="Tipo de Movimento"
                      value={filterMovementType}
                      onChange={(e) => setFilterMovementType(e.target.value)}
                      fullWidth
                      size="small"
                    >
                      <MenuItem value="">— Todos —</MenuItem>
                      {Object.entries(movementTypeLabels).map(([key, label]) => (
                        <MenuItem key={key} value={key}>
                          {label}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Stack>

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                    <TextField
                      label="Data de (opcional)"
                      type="date"
                      value={filterDateFrom}
                      onChange={(e) => setFilterDateFrom(e.target.value)}
                      fullWidth
                      size="small"
                      slotProps={{
                        inputLabel: { shrink: true },
                      }}
                    />

                    <TextField
                      label="Data até (opcional)"
                      type="date"
                      value={filterDateTo}
                      onChange={(e) => setFilterDateTo(e.target.value)}
                      fullWidth
                      size="small"
                      slotProps={{
                        inputLabel: { shrink: true },
                      }}
                    />
                  </Stack>

                  {(filterAssetId || filterMovementType || filterDateFrom || filterDateTo) && (
                    <Button
                      size="small"
                      onClick={() => {
                        setFilterAssetId('')
                        setFilterMovementType('')
                        setFilterDateFrom('')
                        setFilterDateTo('')
                      }}
                    >
                      Limpar filtros
                    </Button>
                  )}
                </Stack>
              </CardContent>
            </Card>

            {/* Movements List */}
            <Card>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                  Movimentações ({filteredMovements.length})
                </Typography>
                {filteredMovements.length === 0 ? (
                  <Box sx={{ py: 4, textAlign: 'center', color: 'text.secondary' }}>
                    <Typography variant="body2">
                      {movements.length === 0
                        ? 'Nenhuma movimentação registrada.'
                        : 'Nenhuma movimentação corresponde aos filtros.'}
                    </Typography>
                  </Box>
                ) : (
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow sx={{ bgcolor: 'action.hover' }}>
                          <TableCell sx={{ fontWeight: 700 }}>Data</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Ticker</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>
                            Quantidade
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>
                            Preço Unitário
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>
                            Valor Total
                          </TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>
                            Ações
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {filteredMovements.map((movement) => {
                          const asset = assets.find((a) => a.id === movement.asset_id)
                          return (
                            <TableRow key={movement.id}>
                              <TableCell>
                                <Typography variant="body2">
                                  {formatDate(movement.date)}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {asset?.ticker || '—'}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={movementTypeLabels[movement.movement_type] || movement.movement_type}
                                  size="small"
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {movement.quantity.toLocaleString('pt-BR', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                  })}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2">
                                  {movement.unit_price !== null
                                    ? currencyFormatter.format(movement.unit_price)
                                    : '—'}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                  {currencyFormatter.format(movement.total_value)}
                                </Typography>
                              </TableCell>
                              <TableCell align="center">
                                <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'center' }}>
                                  <IconButton
                                    size="small"
                                    onClick={() => openEditForm(movement)}
                                  >
                                    <EditOutlinedIcon fontSize="small" />
                                  </IconButton>
                                  <IconButton
                                    size="small"
                                    onClick={() => setPendingDeleteMovement(movement)}
                                  >
                                    <DeleteOutlineIcon fontSize="small" />
                                  </IconButton>
                                </Stack>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </Stack>

      {/* FAB for manual entry */}
      <Fab
        color="primary"
        aria-label="Adicionar movimento"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      {/* Manual Movement Dialog */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editingMovement ? 'Editar movimentação' : 'Nova movimentação'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <TextField
              label="Ticker"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
              placeholder="Ex: PETR4"
              fullWidth
              autoFocus
              disabled={editingMovement !== null}
            />

            {!editingMovement && (
              <TextField
                select
                label="Tipo de ativo"
                value={newAssetType}
                onChange={(e) => setNewAssetType(e.target.value as AssetType)}
                fullWidth
              >
                {Object.entries(assetTypeLabels).map(([key, label]) => (
                  <MenuItem key={key} value={key}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
            )}

            <TextField
              select
              label="Tipo de movimento"
              value={form.movement_type}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  movement_type: e.target.value as MovementType,
                }))
              }
              fullWidth
            >
              {Object.entries(movementTypeLabels).map(([key, label]) => (
                <MenuItem key={key} value={key}>
                  {label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Data"
              type="date"
              value={form.date}
              onChange={(e) => setForm((prev) => ({ ...prev, date: e.target.value }))}
              fullWidth
              slotProps={{
                inputLabel: { shrink: true },
              }}
            />

            <TextField
              label="Quantidade"
              inputMode="decimal"
              placeholder="0,00"
              value={form.quantity || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, quantity: Number(e.target.value) }))
              }
              fullWidth
              slotProps={{
                input: {
                  inputProps: {
                    min: 0.01,
                    step: 0.01,
                  },
                },
              }}
            />

            <TextField
              label="Preço unitário (opcional)"
              inputMode="decimal"
              placeholder="0,00"
              value={form.unit_price || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  unit_price: e.target.value ? Number(e.target.value) : null,
                }))
              }
              fullWidth
              slotProps={{
                input: {
                  inputProps: {
                    min: 0.01,
                    step: 0.01,
                  },
                },
              }}
            />

            <TextField
              label="Valor total"
              inputMode="decimal"
              placeholder="0,00"
              value={form.total_value || ''}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, total_value: Number(e.target.value) }))
              }
              fullWidth
              slotProps={{
                input: {
                  inputProps: {
                    min: 0.01,
                    step: 0.01,
                  },
                },
              }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setFormOpen(false)} disabled={submitting}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleSubmitMovement} disabled={submitting}>
            {editingMovement ? 'Salvar' : 'Adicionar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Movement Dialog */}
      <Dialog open={Boolean(pendingDeleteMovement)} onClose={() => setPendingDeleteMovement(null)}>
        <DialogTitle>Excluir movimentação?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja excluir esta movimentação? Essa ação não pode ser desfeita.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setPendingDeleteMovement(null)} disabled={deletingMovement}>
            Cancelar
          </Button>
          <Button color="error" variant="contained" onClick={confirmDeleteMovement} disabled={deletingMovement}>
            Excluir
          </Button>
        </DialogActions>
      </Dialog>
    </Layout>
  )
}
