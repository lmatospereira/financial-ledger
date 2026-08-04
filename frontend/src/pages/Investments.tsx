import { useEffect, useRef, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import { BarChart } from '@mui/x-charts/BarChart'
import { PieChart } from '@mui/x-charts/PieChart'
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
  useTheme,
} from '@mui/material'
import Layout from '../components/Layout'
import {
  createAsset,
  createInvestmentMovement,
  deleteInvestmentMovement,
  getApiErrorMessage,
  getAssets,
  getInvestmentMovements,
  getPortfolio,
  importInvestmentsFile,
  updateAsset,
  updateInvestmentMovement,
} from '../api/client'
import type {
  Asset,
  AssetType,
  InvestmentMovement,
  InvestmentMovementInput,
  ImportPreviewResponse,
  MovementType,
  PortfolioPosition,
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

export default function Investments() {
  const theme = useTheme()
  const [portfolio, setPortfolio] = useState<PortfolioPosition[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [movements, setMovements] = useState<InvestmentMovement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Manual movement form dialog
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<InvestmentMovementInput>(emptyMovementForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [newTicker, setNewTicker] = useState<string>('')
  const [newAssetType, setNewAssetType] = useState<AssetType>('acao')
  const [editingMovement, setEditingMovement] = useState<InvestmentMovement | null>(null)

  // B3 import dialog
  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const [importStep, setImportStep] = useState<'upload' | 'preview' | 'result'>(
    'upload',
  )
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPreview, setImportPreview] = useState<ImportPreviewResponse | null>(null)
  const [importColumnMapping, setImportColumnMapping] = useState<Record<string, string | null>>(
    {},
  )
  const [showManualMapping, setShowManualMapping] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [importLoading, setImportLoading] = useState(false)
  const [importResult, setImportResult] = useState<{
    assets_created: number
    movements_created: number
  } | null>(null)

  // Edit current price dialog
  const [priceEditPosition, setPriceEditPosition] = useState<PortfolioPosition | null>(null)
  const [priceEditValue, setPriceEditValue] = useState<string>('')
  const [priceEditLoading, setPriceEditLoading] = useState(false)
  const [priceEditError, setPriceEditError] = useState<string | null>(null)

  // Delete movement dialog
  const [pendingDeleteMovement, setPendingDeleteMovement] = useState<InvestmentMovement | null>(null)
  const [deletingMovement, setDeletingMovement] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [portfolioData, assetsData, movementsData] = await Promise.all([
        getPortfolio(),
        getAssets(),
        getInvestmentMovements(),
      ])
      setPortfolio(portfolioData)
      setAssets(assetsData)
      setMovements(movementsData)
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

  const openPriceEdit = (position: PortfolioPosition) => {
    setPriceEditPosition(position)
    setPriceEditValue(position.current_price ? position.current_price.toString() : '')
    setPriceEditError(null)
  }

  const handleSavePrice = async () => {
    if (!priceEditPosition) return

    setPriceEditError(null)
    const newPrice = priceEditValue.trim() ? Number(priceEditValue) : null

    if (priceEditValue.trim() && (isNaN(newPrice as number) || (newPrice !== null && newPrice <= 0))) {
      setPriceEditError('Informe um valor válido maior que zero.')
      return
    }

    setPriceEditLoading(true)
    try {
      const asset = assets.find((a) => a.ticker === priceEditPosition.ticker)
      if (asset) {
        await updateAsset(asset.id, {
          ticker: asset.ticker,
          name: asset.name,
          asset_type: asset.asset_type,
          current_price: newPrice,
        })
        await loadData()
        setPriceEditPosition(null)
      }
    } catch (err) {
      setPriceEditError(getApiErrorMessage(err))
    } finally {
      setPriceEditLoading(false)
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

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImportFile(file)
    setImportColumnMapping({})
    setShowManualMapping(false)
    setImportError(null)
    setImportStep('preview')

    // Call import without column_mapping for preview
    setImportLoading(true)
    try {
      const response = await importInvestmentsFile(file)
      if (response.committed === false) {
        setImportPreview(response)
        setImportColumnMapping(response.detected_mapping || {})
        // Known B3 layout: the mapping is certain, so default to the
        // one-click confirmation instead of asking the user to review
        // every column -- they can still expand it manually if they want.
        setShowManualMapping(!response.is_known_b3_format)
      }
    } catch (err) {
      setImportError(getApiErrorMessage(err))
      setImportStep('upload')
    } finally {
      setImportLoading(false)
    }
  }

  const handleConfirmImport = async () => {
    if (!importFile) return

    // Validate all required fields are mapped
    const requiredFields = ['date', 'movement_type', 'ticker', 'quantity', 'total_value']
    const unmappedField = requiredFields.find((field) => !importColumnMapping[field])
    if (unmappedField) {
      setImportError(`O campo "${unmappedField}" não foi mapeado.`)
      return
    }

    setImportLoading(true)
    setImportError(null)
    try {
      const mappingToSubmit = Object.fromEntries(
        Object.entries(importColumnMapping).filter(([, v]) => v !== null)
      ) as Record<string, string>
      const response = await importInvestmentsFile(importFile, mappingToSubmit)
      if (response.committed === true) {
        setImportResult({
          assets_created: response.assets_created,
          movements_created: response.movements_created,
        })
        setImportStep('result')
        await loadData()
      }
    } catch (err) {
      setImportError(getApiErrorMessage(err))
    } finally {
      setImportLoading(false)
    }
  }

  const closeImportDialog = () => {
    setImportDialogOpen(false)
    setImportStep('upload')
    setImportFile(null)
    setImportPreview(null)
    setImportColumnMapping({})
    setShowManualMapping(false)
    setImportError(null)
    setImportResult(null)
  }

  // Calculate portfolio composition data for pie chart
  const compositionData = portfolio
    .filter((pos) => pos.total_invested > 0)
    .map((pos) => ({
      id: pos.ticker,
      value: pos.total_invested,
      label: pos.ticker,
    }))

  // Calculate profitability report data
  const positionsWithPrice = portfolio.filter((pos) => pos.current_price !== null)
  const totalInvestedWithPrice = positionsWithPrice.reduce((sum, pos) => sum + pos.total_invested, 0)
  const totalCurrentValue = positionsWithPrice.reduce((sum, pos) => sum + (pos.current_value || 0), 0)
  const totalProfitLoss = positionsWithPrice.reduce((sum, pos) => sum + (pos.profit_loss || 0), 0)
  const totalProfitLossPercent = totalInvestedWithPrice > 0 ? (totalProfitLoss / totalInvestedWithPrice) * 100 : 0

  const profitabilityChartData = positionsWithPrice.map((pos) => ({
    ticker: pos.ticker,
    invested: pos.total_invested,
    current: pos.current_value || 0,
  }))

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Investimentos
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        {loading ? (
          <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : portfolio.length === 0 ? (
          <Card>
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <TrendingUpIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">
                Nenhuma posição de investimento.
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Comece adicionando movimentações manualmente ou importe um arquivo B3.
              </Typography>
            </Box>
          </Card>
        ) : (
          <>
            {/* Composition Chart */}
            <Card>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                  Composição da Carteira
                </Typography>
                {compositionData.length === 0 ? (
                  <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>
                    <Typography variant="body1">
                      Nenhuma posição com valor investido.
                    </Typography>
                  </Box>
                ) : (
                  <PieChart
                    height={300}
                    series={[
                      {
                        data: compositionData,
                        innerRadius: 50,
                        paddingAngle: 2,
                        cornerRadius: 4,
                        valueFormatter: (item: { value: number }) =>
                          currencyFormatter.format(item.value),
                      },
                    ]}
                    slotProps={{
                      legend: { direction: 'vertical', position: { vertical: 'middle', horizontal: 'end' } },
                    }}
                  />
                )}
              </CardContent>
            </Card>

            {/* Portfolio Table with Price Editing */}
            <TableContainer component={Card}>
              <Table>
                <TableHead>
                  <TableRow sx={{ bgcolor: 'action.hover' }}>
                    <TableCell sx={{ fontWeight: 700 }}>Ticker</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      Quantidade
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      Preço Médio
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      Total Investido
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      Preço Atual
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      Valor Atual
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      Lucro/Prejuízo
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {portfolio.map((position) => (
                    <TableRow key={position.ticker}>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {position.ticker}
                          </Typography>
                          {position.name && (
                            <Typography variant="caption" color="text.secondary">
                              {position.name}
                            </Typography>
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={assetTypeLabels[position.asset_type as AssetType] || position.asset_type}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {position.quantity_held.toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {currencyFormatter.format(position.avg_price)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {currencyFormatter.format(position.total_invested)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end', alignItems: 'center' }}>
                          {position.current_price !== null ? (
                            <>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {currencyFormatter.format(position.current_price)}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => openPriceEdit(position)}
                                sx={{ ml: 0.5 }}
                              >
                                <EditOutlinedIcon fontSize="small" />
                              </IconButton>
                            </>
                          ) : (
                            <>
                              <Typography variant="body2" color="text.secondary">
                                —
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => openPriceEdit(position)}
                              >
                                <EditOutlinedIcon fontSize="small" />
                              </IconButton>
                            </>
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            color: position.current_value === null ? 'text.secondary' : undefined,
                          }}
                        >
                          {position.current_value !== null
                            ? currencyFormatter.format(position.current_value)
                            : '—'}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack spacing={0.25}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 600,
                              color:
                                position.profit_loss === null
                                  ? 'text.secondary'
                                  : position.profit_loss >= 0
                                    ? 'success.main'
                                    : 'error.main',
                            }}
                          >
                            {position.profit_loss !== null
                              ? currencyFormatter.format(position.profit_loss)
                              : '—'}
                          </Typography>
                          {position.profit_loss_pct !== null && (
                            <Typography
                              variant="caption"
                              sx={{
                                color: position.profit_loss_pct >= 0 ? 'success.main' : 'error.main',
                              }}
                            >
                              {position.profit_loss_pct >= 0 ? '+' : ''}
                              {position.profit_loss_pct.toFixed(2)}%
                            </Typography>
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Profitability Report */}
            {positionsWithPrice.length > 0 && (
              <>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                      Rentabilidade
                    </Typography>
                    <Stack spacing={2}>
                      <Typography variant="body2" color="text.secondary">
                        {positionsWithPrice.length} de {portfolio.length} ativos com preço atual informado
                      </Typography>
                      <Stack direction="row" spacing={3}>
                        <Stack>
                          <Typography variant="caption" color="text.secondary">
                            Total Investido
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 700 }}>
                            {currencyFormatter.format(totalInvestedWithPrice)}
                          </Typography>
                        </Stack>
                        <Stack>
                          <Typography variant="caption" color="text.secondary">
                            Valor Atual
                          </Typography>
                          <Typography variant="h6" sx={{ fontWeight: 700 }}>
                            {currencyFormatter.format(totalCurrentValue)}
                          </Typography>
                        </Stack>
                        <Stack>
                          <Typography variant="caption" color="text.secondary">
                            Lucro/Prejuízo
                          </Typography>
                          <Typography
                            variant="h6"
                            sx={{
                              fontWeight: 700,
                              color: totalProfitLoss >= 0 ? 'success.main' : 'error.main',
                            }}
                          >
                            {currencyFormatter.format(totalProfitLoss)}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{
                              color: totalProfitLoss >= 0 ? 'success.main' : 'error.main',
                            }}
                          >
                            {totalProfitLoss >= 0 ? '+' : ''}
                            {totalProfitLossPercent.toFixed(2)}%
                          </Typography>
                        </Stack>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                      Valor Investido vs Valor Atual
                    </Typography>
                    <BarChart
                      height={300}
                      dataset={profitabilityChartData}
                      xAxis={[{ scaleType: 'band', dataKey: 'ticker' }]}
                      series={[
                        {
                          dataKey: 'invested',
                          label: 'Investido',
                          color: theme.palette.primary.main,
                          valueFormatter: (value: number | null) =>
                            currencyFormatter.format(value ?? 0),
                        },
                        {
                          dataKey: 'current',
                          label: 'Valor Atual',
                          color: theme.palette.success.main,
                          valueFormatter: (value: number | null) =>
                            currencyFormatter.format(value ?? 0),
                        },
                      ]}
                      slotProps={{ legend: { position: { vertical: 'top', horizontal: 'end' } } }}
                      margin={{ top: 40 }}
                    />
                  </CardContent>
                </Card>
              </>
            )}

            {positionsWithPrice.length === 0 && (
              <Card>
                <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>
                  <Typography variant="body1">
                    Informe o preço atual dos seus ativos para acompanhar a rentabilidade.
                  </Typography>
                </Box>
              </Card>
            )}

            {/* Movements List */}
            <Card>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                  Movimentações
                </Typography>
                {movements.length === 0 ? (
                  <Box sx={{ py: 4, textAlign: 'center', color: 'text.secondary' }}>
                    <Typography variant="body2">
                      Nenhuma movimentação registrada.
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
                        {movements.map((movement) => {
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

      {/* B3 Import Button */}
      <Button
        variant="contained"
        startIcon={<CloudUploadIcon />}
        onClick={() => setImportDialogOpen(true)}
        sx={{ position: 'fixed', bottom: 24, right: 96 }}
      >
        Importar B3
      </Button>

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

      {/* Edit Current Price Dialog */}
      <Dialog open={Boolean(priceEditPosition)} onClose={() => setPriceEditPosition(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Editar Preço Atual</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {priceEditError && <Alert severity="error">{priceEditError}</Alert>}
            <Typography variant="body2" color="text.secondary">
              {priceEditPosition?.ticker}
            </Typography>
            <TextField
              label="Preço Atual (R$)"
              inputMode="decimal"
              placeholder="0,00"
              value={priceEditValue}
              onChange={(e) => setPriceEditValue(e.target.value)}
              fullWidth
              autoFocus
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
          <Button onClick={() => setPriceEditPosition(null)} disabled={priceEditLoading}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleSavePrice} disabled={priceEditLoading}>
            Salvar
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

      {/* B3 Import Dialog */}
      <Dialog
        open={importDialogOpen}
        onClose={closeImportDialog}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Importar arquivo B3</DialogTitle>
        <DialogContent>
          {importStep === 'upload' && (
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              {importError && <Alert severity="error">{importError}</Alert>}

              <Typography variant="body2" color="text.secondary">
                Selecione um arquivo CSV ou XLSX exportado da B3.
              </Typography>

              <Button
                variant="outlined"
                component="label"
                fullWidth
                startIcon={<CloudUploadIcon />}
              >
                Escolher arquivo
                <input
                  ref={fileInputRef}
                  hidden
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleFileSelect}
                />
              </Button>
            </Stack>
          )}

          {importStep === 'preview' && importPreview && (
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              {importError && <Alert severity="error">{importError}</Alert>}

              {importPreview.is_known_b3_format ? (
                <Alert severity="success">
                  Formato oficial da B3 (Movimentação) reconhecido — {importPreview.row_count}{' '}
                  {importPreview.row_count === 1 ? 'linha pronta' : 'linhas prontas'} para importar.
                </Alert>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Confira o mapeamento de colunas antes de importar.
                </Typography>
              )}

              {!importPreview.is_known_b3_format && (
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
                    Total de linhas: {importPreview.row_count}
                  </Typography>
                </Box>
              )}

              {importPreview.is_known_b3_format && !showManualMapping && (
                <Button
                  size="small"
                  onClick={() => setShowManualMapping(true)}
                  sx={{ alignSelf: 'flex-start' }}
                >
                  Ajustar mapeamento manualmente
                </Button>
              )}

              {showManualMapping && (
                <>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 2 }}>
                    Mapeamento de colunas
                  </Typography>

                  <Stack spacing={1.5}>
                    {['date', 'movement_type', 'ticker', 'quantity', 'unit_price', 'total_value'].map(
                      (field) => (
                        <TextField
                          key={field}
                          select
                          label={field}
                          value={importColumnMapping[field] || ''}
                          onChange={(e) =>
                            setImportColumnMapping((prev) => ({
                              ...prev,
                              [field]: e.target.value,
                            }))
                          }
                          fullWidth
                          size="small"
                        >
                          <MenuItem value="">— Não mapeado —</MenuItem>
                          {importPreview.raw_columns.map((col) => (
                            <MenuItem key={col} value={col}>
                              {col}
                            </MenuItem>
                          ))}
                        </TextField>
                      ),
                    )}
                  </Stack>
                </>
              )}

              {importPreview.sample_rows.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
                    Amostra de dados
                  </Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow sx={{ bgcolor: 'action.hover' }}>
                          {importPreview.raw_columns.map((col) => (
                            <TableCell key={col} sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                              {col}
                            </TableCell>
                          ))}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {importPreview.sample_rows.slice(0, 3).map((row, idx) => (
                          <TableRow key={idx}>
                            {importPreview.raw_columns.map((col) => (
                              <TableCell key={col} sx={{ fontSize: '0.75rem' }}>
                                {row[col] || '—'}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </Stack>
          )}

          {importStep === 'result' && importResult && (
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              <Alert severity="success">
                Importação concluída com sucesso!
              </Alert>

              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Ativos criados: {importResult.assets_created}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, mt: 1 }}>
                  Movimentações importadas: {importResult.movements_created}
                </Typography>
              </Box>
            </Stack>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          {importStep === 'upload' && (
            <Button onClick={closeImportDialog}>
              Cancelar
            </Button>
          )}
          {importStep === 'preview' && (
            <>
              <Button onClick={() => setImportStep('upload')} disabled={importLoading}>
                Voltar
              </Button>
              <Button
                variant="contained"
                onClick={handleConfirmImport}
                disabled={importLoading}
              >
                {importLoading ? 'Importando...' : 'Confirmar importação'}
              </Button>
            </>
          )}
          {importStep === 'result' && (
            <Button variant="contained" onClick={closeImportDialog}>
              Fechar
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Layout>
  )
}
