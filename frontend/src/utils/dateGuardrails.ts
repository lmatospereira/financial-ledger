/**
 * Returns min and max ISO date strings for dates within 3 years before/after today.
 * Useful for date input constraints.
 */
export function getDateGuardrails(): { min: string; max: string } {
  const today = new Date()

  const minDate = new Date(today)
  minDate.setFullYear(minDate.getFullYear() - 3)

  const maxDate = new Date(today)
  maxDate.setFullYear(maxDate.getFullYear() + 3)

  return {
    min: minDate.toISOString().split('T')[0],
    max: maxDate.toISOString().split('T')[0],
  }
}
