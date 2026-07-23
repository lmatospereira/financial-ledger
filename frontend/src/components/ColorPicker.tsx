import { Box, Stack, TextField, Typography } from '@mui/material'
import { PRESET_COLORS } from './colors'

interface ColorPickerProps {
  value: string
  onChange: (color: string) => void
  label?: string
}

export default function ColorPicker({ value, onChange, label = 'Cor' }: ColorPickerProps) {
  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {label}
      </Typography>
      <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap', mb: 1.5 }}>
        {PRESET_COLORS.map((color) => (
          <Box
            key={color}
            onClick={() => onChange(color)}
            sx={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              bgcolor: color,
              cursor: 'pointer',
              border: (theme) =>
                value === color
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
          value={value}
          onChange={(e) => onChange(e.target.value)}
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
          value={value}
          onChange={(e) => onChange(e.target.value)}
          sx={{ flexGrow: 1 }}
        />
      </Stack>
    </Box>
  )
}
