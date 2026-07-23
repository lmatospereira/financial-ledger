import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import { IconButton, Stack, Typography } from '@mui/material'

const MONTH_NAMES = [
  'Janeiro',
  'Fevereiro',
  'Março',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
]

interface MonthSelectorProps {
  month: number // 1-12
  year: number
  onChange: (month: number, year: number) => void
}

export default function MonthSelector({
  month,
  year,
  onChange,
}: MonthSelectorProps) {
  const goToPrevious = () => {
    if (month === 1) {
      onChange(12, year - 1)
    } else {
      onChange(month - 1, year)
    }
  }

  const goToNext = () => {
    if (month === 12) {
      onChange(1, year + 1)
    } else {
      onChange(month + 1, year)
    }
  }

  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{ alignItems: 'center', justifyContent: 'center' }}
    >
      <IconButton aria-label="Mês anterior" onClick={goToPrevious}>
        <ChevronLeftIcon />
      </IconButton>
      <Typography variant="h6" sx={{ minWidth: 180, textAlign: 'center' }}>
        {MONTH_NAMES[month - 1]} {year}
      </Typography>
      <IconButton aria-label="Próximo mês" onClick={goToNext}>
        <ChevronRightIcon />
      </IconButton>
    </Stack>
  )
}
