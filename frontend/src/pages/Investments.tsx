import { useEffect, useRef, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
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
  DialogTitle,
  Fab,
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
  getApiErrorMessage,
  getPortfolio,
  importInvestmentsFile,
} from '../api/client'
import type {
  AssetType,
  InvestmentMovementInput,
  ImportPreviewResponse,
  PortfolioPosition,
} from '../api/types'

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
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

const emptyMovementForm: InvestmentMovementInput = {
  asset_id: 0,
  date: new Date().toISOString().split('T')[0],
  movement_type: 'compra',
  quantity: 0,
  unit_price: null,
  total_value: 0,
}

export default function Investments() {
  const [portfolio, setPortfolio] = useState<PortfolioPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Manual movement form dialog
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<InvestmentMovementInput>(emptyMovementForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [newTicker, setNewTicker] = useState<string>('')
  const [newAssetType, setNewAssetType] = useState<AssetType>('acao')

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
  const [importError, setImportError] = useState<string | null>(null)
  const [importLoading, setImportLoading] = useState(false)
  const [importResult, setImportResult] = useState<{
    assets_created: number
    movements_created: number
  } | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const portfolioData = await getPortfolio()
      setPortfolio(portfolioData)
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
    setForm(emptyMovementForm)
    setNewTicker('')
    setNewAssetType('acao')
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

    // If using a new ticker, create the asset first
    let assetId = form.asset_id
    if (newTicker && (!form.asset_id || form.asset_id === 0)) {
      try {
        setSubmitting(true)
        const newAsset = await createAsset({
          ticker: newTicker.toUpperCase(),
          name: null,
          asset_type: newAssetType,
        })
        assetId = newAsset.id
      } catch (err) {
        setFormError(getApiErrorMessage(err))
        setSubmitting(false)
        return
      }
    }

    if (!assetId || assetId === 0) {
      setFormError('Selecione ou informe um ticker.')
      setSubmitting(false)
      return
    }

    setSubmitting(true)
    try {
      await createInvestmentMovement({
        ...form,
        asset_id: assetId,
      })
      setFormOpen(false)
      await loadData()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImportFile(file)
    setImportColumnMapping({})
    setImportError(null)
    setImportStep('preview')

    // Call import without column_mapping for preview
    setImportLoading(true)
    try {
      const response = await importInvestmentsFile(file)
      if (response.committed === false) {
        setImportPreview(response)
        setImportColumnMapping(response.detected_mapping || {})
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
    setImportError(null)
    setImportResult(null)
  }

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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
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
        <DialogTitle>Nova movimentação</DialogTitle>
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
            />

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

            <TextField
              select
              label="Tipo de movimento"
              value={form.movement_type}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, movement_type: e.target.value as any }))
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
            Adicionar
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

              <Typography variant="body2" color="text.secondary">
                Confira o mapeamento de colunas antes de importar.
              </Typography>

              <Box>
                <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
                  Total de linhas: {importPreview.row_count}
                </Typography>
              </Box>

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
