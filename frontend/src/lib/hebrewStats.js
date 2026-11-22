/** Pure helpers for the Hebrew stats panel (B3). Vitest-covered. */

export function retentionPct(rate) {
  if (rate == null || Number.isNaN(rate)) return '—'
  return `${Math.round(rate * 100)}%`
}

export function forecastMax(forecast) {
  if (!forecast || forecast.length === 0) return 1
  return Math.max(1, ...forecast.map(f => f.due || 0))
}

export function heatmapMax(heatmap) {
  if (!heatmap || heatmap.length === 0) return 1
  return Math.max(1, ...heatmap.map(h => h.reviews || 0))
}

/** Total scheduled reviews on the forecast horizon. */
export function forecastTotal(forecast) {
  if (!forecast) return 0
  return forecast.reduce((s, f) => s + (f.due || 0), 0)
}
