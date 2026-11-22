import { describe, it, expect } from 'vitest'
import { retentionPct, forecastMax, heatmapMax, forecastTotal } from '../lib/hebrewStats'

describe('hebrewStats helpers (B3 panel)', () => {
  it('formats retention rates, em-dash when unknown', () => {
    expect(retentionPct(0.9)).toBe('90%')
    expect(retentionPct(0.856)).toBe('86%')
    expect(retentionPct(null)).toBe('—')
    expect(retentionPct(undefined)).toBe('—')
  })

  it('computes bar maxima with a floor of 1', () => {
    expect(forecastMax([])).toBe(1)
    expect(forecastMax([{ due: 0 }, { due: 5 }])).toBe(5)
    expect(heatmapMax([{ reviews: 0 }])).toBe(1)
    expect(heatmapMax([{ reviews: 3 }, { reviews: 9 }])).toBe(9)
  })

  it('totals the forecast horizon', () => {
    expect(forecastTotal([{ due: 2 }, { due: 3 }])).toBe(5)
    expect(forecastTotal(null)).toBe(0)
  })
})
