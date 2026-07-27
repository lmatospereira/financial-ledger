import { useRef, useState } from 'react'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import {
  Button,
  IconButton,
  Popover,
  Stack,
  Typography,
  useTheme,
} from '@mui/material'

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

const MONTH_SHORT = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
]

interface MonthSelectorProps {
  month: number // 1-12
  year: number
  onChange: (month: number, year: number) => void
}

function getCurrentPeriod(): { month: number; year: number } {
  const now = new Date()
  return { month: now.getMonth() + 1, year: now.getFullYear() }
}

export default function MonthSelector({
  month,
  year,
  onChange,
}: MonthSelectorProps) {
  const theme = useTheme()
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const [popoverYear, setPopoverYear] = useState(year)
  const touchStartX = useRef(0)
  const touchStartY = useRef(0)

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

  const handleLabelClick = (e: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(e.currentTarget)
    setPopoverYear(year)
  }

  const handlePopoverClose = () => {
    setAnchorEl(null)
  }

  const handleMonthSelect = (selectedMonth: number) => {
    onChange(selectedMonth, popoverYear)
    handlePopoverClose()
  }

  const handleTodayClick = () => {
    const today = getCurrentPeriod()
    onChange(today.month, today.year)
    handlePopoverClose()
  }

  const handlePrevYear = () => {
    setPopoverYear(popoverYear - 1)
  }

  const handleNextYear = () => {
    setPopoverYear(popoverYear + 1)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      goToPrevious()
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      goToNext()
    }
  }

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
  }

  const handleTouchEnd = (e: React.TouchEvent) => {
    const touchEndX = e.changedTouches[0].clientX
    const touchEndY = e.changedTouches[0].clientY
    const deltaX = touchEndX - touchStartX.current
    const deltaY = touchEndY - touchStartY.current

    // Only trigger swipe if horizontal movement is greater than vertical
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
      if (deltaX < 0) {
        // Swipe left → next month
        goToNext()
      } else {
        // Swipe right → previous month
        goToPrevious()
      }
    }
  }

  const open = Boolean(anchorEl)

  return (
    <Stack
      direction="row"
      spacing={1}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      sx={{
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 1,
        outline: 'none',
        '&:focus-visible': {
          outline: `2px solid ${theme.palette.primary.main}`,
          outlineOffset: 2,
        },
      }}
    >
      <IconButton aria-label="Mês anterior" onClick={goToPrevious}>
        <ChevronLeftIcon />
      </IconButton>
      <Typography
        variant="h6"
        onClick={handleLabelClick}
        sx={{
          minWidth: 180,
          textAlign: 'center',
          cursor: 'pointer',
          borderRadius: 1,
          px: 1,
          py: 0.5,
          transition: 'background-color 0.2s',
          '&:hover': {
            backgroundColor: theme.palette.action.hover,
          },
        }}
      >
        {MONTH_NAMES[month - 1]} {year}
      </Typography>
      <IconButton aria-label="Próximo mês" onClick={goToNext}>
        <ChevronRightIcon />
      </IconButton>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handlePopoverClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'center',
        }}
      >
        <Stack spacing={2} sx={{ p: 2 }}>
          <Stack
            direction="row"
            spacing={2}
            sx={{ alignItems: 'center', justifyContent: 'space-between' }}
          >
            <IconButton
              size="small"
              onClick={handlePrevYear}
              aria-label="Ano anterior"
            >
              <ChevronLeftIcon fontSize="small" />
            </IconButton>
            <Typography variant="h6" sx={{ minWidth: 60, textAlign: 'center' }}>
              {popoverYear}
            </Typography>
            <IconButton
              size="small"
              onClick={handleNextYear}
              aria-label="Próximo ano"
            >
              <ChevronRightIcon fontSize="small" />
            </IconButton>
          </Stack>

          <Stack spacing={1}>
            {/* First row: Jan-Apr */}
            <Stack direction="row" spacing={1}>
              {MONTH_SHORT.slice(0, 4).map((monthShort, idx) => {
                const monthNum = idx + 1
                const isSelected = monthNum === month && popoverYear === year
                return (
                  <Button
                    key={monthNum}
                    fullWidth
                    size="small"
                    onClick={() => handleMonthSelect(monthNum)}
                    variant={isSelected ? 'contained' : 'outlined'}
                    sx={{ borderRadius: 1 }}
                  >
                    {monthShort}
                  </Button>
                )
              })}
            </Stack>
            {/* Second row: May-Aug */}
            <Stack direction="row" spacing={1}>
              {MONTH_SHORT.slice(4, 8).map((monthShort, idx) => {
                const monthNum = idx + 5
                const isSelected = monthNum === month && popoverYear === year
                return (
                  <Button
                    key={monthNum}
                    fullWidth
                    size="small"
                    onClick={() => handleMonthSelect(monthNum)}
                    variant={isSelected ? 'contained' : 'outlined'}
                    sx={{ borderRadius: 1 }}
                  >
                    {monthShort}
                  </Button>
                )
              })}
            </Stack>
            {/* Third row: Sep-Dec */}
            <Stack direction="row" spacing={1}>
              {MONTH_SHORT.slice(8, 12).map((monthShort, idx) => {
                const monthNum = idx + 9
                const isSelected = monthNum === month && popoverYear === year
                return (
                  <Button
                    key={monthNum}
                    fullWidth
                    size="small"
                    onClick={() => handleMonthSelect(monthNum)}
                    variant={isSelected ? 'contained' : 'outlined'}
                    sx={{ borderRadius: 1 }}
                  >
                    {monthShort}
                  </Button>
                )
              })}
            </Stack>
          </Stack>

          <Button
            fullWidth
            variant="contained"
            size="small"
            onClick={handleTodayClick}
          >
            Hoje
          </Button>
        </Stack>
      </Popover>
    </Stack>
  )
}
