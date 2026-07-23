import { useEffect, useState } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlineOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import LabelOutlinedIcon from '@mui/icons-material/LabelOutlined'
import {
  Alert,
  Box,
  Button,
  Card,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  Fab,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import Layout from '../components/Layout'
import {
  createCategory,
  deleteCategory,
  getApiErrorMessage,
  getCategories,
  updateCategory,
} from '../api/client'
import type { Category, CategoryInput } from '../api/types'

const PRESET_COLORS = [
  '#EF5350',
  '#EC407A',
  '#AB47BC',
  '#7E57C2',
  '#5C6BC0',
  '#42A5F5',
  '#29B6F6',
  '#26C6DA',
  '#26A69A',
  '#66BB6A',
  '#9CCC65',
  '#D4E157',
  '#FFEE58',
  '#FFCA28',
  '#FFA726',
  '#FF7043',
  '#8D6E63',
  '#78909C',
]

const emptyForm: CategoryInput = {
  name: '',
  color: PRESET_COLORS[4],
  type: 'expense',
}

export default function Categories() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Category | null>(null)
  const [form, setForm] = useState<CategoryInput>(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [pendingDelete, setPendingDelete] = useState<Category | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadCategories = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getCategories()
      setCategories(data)
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
  }, [])

  const openCreateForm = () => {
    setEditing(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (category: Category) => {
    setEditing(category)
    setForm({ name: category.name, color: category.color, type: category.type })
    setFormError(null)
    setFormOpen(true)
  }

  const handleSubmit = async () => {
    setFormError(null)
    if (!form.name.trim()) {
      setFormError('Informe um nome para a categoria.')
      return
    }

    setSubmitting(true)
    try {
      if (editing) {
        await updateCategory(editing.id, form)
      } else {
        await createCategory(form)
      }
      setFormOpen(false)
      await loadCategories()
    } catch (err) {
      setFormError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteCategory(pendingDelete.id)
      setPendingDelete(null)
      await loadCategories()
    } catch (err) {
      setError(getApiErrorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Layout>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Categorias
        </Typography>

        {error && <Alert severity="error">{error}</Alert>}

        <Card>
          {loading ? (
            <Box sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : categories.length === 0 ? (
            <Box sx={{ py: 8, textAlign: 'center', color: 'text.secondary' }}>
              <LabelOutlinedIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">Nenhuma categoria cadastrada.</Typography>
            </Box>
          ) : (
            <List disablePadding>
              {categories.map((category, index) => (
                <Box key={category.id}>
                  {index > 0 && <Divider component="li" />}
                  <ListItem
                    sx={{ py: 1.5 }}
                    secondaryAction={
                      <Stack direction="row" spacing={0.5}>
                        <IconButton
                          aria-label="Editar"
                          size="small"
                          onClick={() => openEditForm(category)}
                        >
                          <EditOutlinedIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          aria-label="Excluir"
                          size="small"
                          onClick={() => setPendingDelete(category)}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    }
                  >
                    <Box
                      sx={{
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        bgcolor: category.color,
                        mr: 2,
                        flexShrink: 0,
                      }}
                    />
                    <ListItemText
                      primary={category.name}
                      secondary={category.type === 'income' ? 'Receita' : 'Despesa'}
                    />
                  </ListItem>
                </Box>
              ))}
            </List>
          )}
        </Card>
      </Stack>

      <Fab
        color="primary"
        aria-label="Adicionar categoria"
        onClick={openCreateForm}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{editing ? 'Editar categoria' : 'Nova categoria'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            <ToggleButtonGroup
              color="primary"
              exclusive
              fullWidth
              value={form.type}
              onChange={(_, value) => {
                if (value) setForm((prev) => ({ ...prev, type: value }))
              }}
            >
              <ToggleButton value="income">Receita</ToggleButton>
              <ToggleButton value="expense">Despesa</ToggleButton>
            </ToggleButtonGroup>

            <TextField
              label="Nome"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              fullWidth
              autoFocus
            />

            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Cor
              </Typography>
              <Stack
                direction="row"
                spacing={1}
                useFlexGap
                sx={{ flexWrap: 'wrap', mb: 1.5 }}
              >
                {PRESET_COLORS.map((color) => (
                  <Box
                    key={color}
                    onClick={() => setForm((prev) => ({ ...prev, color }))}
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      bgcolor: color,
                      cursor: 'pointer',
                      border: (theme) =>
                        form.color === color
                          ? `2px solid ${theme.palette.text.primary}`
                          : '2px solid transparent',
                      outline: '1px solid rgba(0,0,0,0.08)',
                      transition: 'transform 0.1s',
                      '&:hover': { transform: 'scale(1.1)' },
                    }}
                  />
                ))}
              </Stack>
              <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                <input
                  type="color"
                  value={form.color}
                  onChange={(e) => setForm((prev) => ({ ...prev, color: e.target.value }))}
                  style={{
                    width: 40,
                    height: 40,
                    border: 'none',
                    borderRadius: 8,
                    padding: 0,
                    background: 'none',
                    cursor: 'pointer',
                  }}
                  aria-label="Cor personalizada"
                />
                <TextField
                  size="small"
                  value={form.color}
                  onChange={(e) => setForm((prev) => ({ ...prev, color: e.target.value }))}
                  sx={{ flexGrow: 1 }}
                />
              </Stack>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setFormOpen(false)} disabled={submitting}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(pendingDelete)} onClose={() => setPendingDelete(null)}>
        <DialogTitle>Excluir categoria?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Tem certeza que deseja excluir “{pendingDelete?.name}”? Essa ação não
            pode ser desfeita.
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
    </Layout>
  )
}
