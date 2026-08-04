import { Box, Card, Typography } from '@mui/material'
import type { ReactNode } from 'react'

interface StatCardProps {
  icon: ReactNode
  label: string
  value: string
  loading?: boolean
  variant?: 'default' | 'positive' | 'negative'
}

export default function StatCard({
  icon,
  label,
  value,
  loading = false,
  variant = 'default',
}: StatCardProps) {

  let iconBgColor = 'primary.main'
  if (variant === 'positive') {
    iconBgColor = 'success.main'
  } else if (variant === 'negative') {
    iconBgColor = 'error.main'
  }

  return (
    <Card
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <Box
        sx={{
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 40,
            height: 40,
            borderRadius: '50%',
            bgcolor: iconBgColor,
            color: 'primary.contrastText',
          }}
        >
          <Box sx={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center' }}>
            {icon}
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
          {label}
        </Typography>

        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            wordBreak: 'break-word',
          }}
        >
          {loading ? '—' : value}
        </Typography>
      </Box>
    </Card>
  )
}
