/**
 * Normalize text input for forms:
 * - First letter/word uppercase
 * - Rest lowercase
 * Examples: "MARKET ALIŞVERIŞI" → "Market alışverişı"
 */
export function normalizeFormText(text: string): string {
  if (!text || typeof text !== 'string') return ''
  const trimmed = text.trim()
  if (trimmed.length === 0) return ''
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase()
}

/**
 * Apply normalization to multiple fields
 */
export function normalizeFormData(data: Record<string, any>, fieldsToNormalize: string[]): Record<string, any> {
  const normalized = { ...data }
  fieldsToNormalize.forEach(field => {
    if (field in normalized && typeof normalized[field] === 'string') {
      normalized[field] = normalizeFormText(normalized[field])
    }
  })
  return normalized
}
