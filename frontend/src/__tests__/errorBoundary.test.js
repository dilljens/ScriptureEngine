import { describe, expect, it } from 'vitest'
import { isChunkLoadError } from '../components/ErrorBoundary'

describe('ErrorBoundary isChunkLoadError (stale-chunk self-heal)', () => {
  it('detects dynamic-import failures', () => {
    expect(isChunkLoadError('Failed to fetch dynamically imported module: /assets/HebrewLearnView-abc.js')).toBe(true)
    expect(isChunkLoadError('Loading chunk 42 failed')).toBe(true)
  })

  it('ignores ordinary render errors', () => {
    expect(isChunkLoadError('Cannot read properties of undefined (reading \'map\')')).toBe(false)
    expect(isChunkLoadError('')).toBe(false)
    expect(isChunkLoadError(null)).toBe(false)
    expect(isChunkLoadError(undefined)).toBe(false)
  })
})
