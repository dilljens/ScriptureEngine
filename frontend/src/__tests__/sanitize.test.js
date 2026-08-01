import { describe, it, expect } from 'vitest'
import { escapeHtml, safeUrlTransform } from '../lib/sanitize'

describe('escapeHtml', () => {
  it('escapes angle brackets so raw HTML is inert', () => {
    expect(escapeHtml('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('escapes quotes and ampersands', () => {
    expect(escapeHtml('a&b"c\'d')).toBe('a&amp;b&quot;c&#39;d')
  })

  it('leaves plain text and scripture markers untouched', () => {
    const text = 'See :verse[gen.1.1] and %%%CLICK:Yom Kippur%%%'
    expect(escapeHtml(text)).toBe(text)
  })

  it('neutralizes attribute-injection attempts', () => {
    const out = escapeHtml('<img src=x onerror=alert(1)>')
    expect(out).not.toContain('<img')
    expect(out).toContain('onerror')
  })

  it('handles null/undefined/numbers', () => {
    expect(escapeHtml(null)).toBe('')
    expect(escapeHtml(undefined)).toBe('')
    expect(escapeHtml(42)).toBe('42')
  })
})

describe('safeUrlTransform', () => {
  it('allows http/https/mailto/relative/anchor', () => {
    expect(safeUrlTransform('https://example.com')).toBe('https://example.com')
    expect(safeUrlTransform('http://example.com')).toBe('http://example.com')
    expect(safeUrlTransform('mailto:a@b.c')).toBe('mailto:a@b.c')
    expect(safeUrlTransform('/gen.1.1')).toBe('/gen.1.1')
    expect(safeUrlTransform('#top')).toBe('#top')
  })

  it('blocks javascript:, data:, vbscript: URLs', () => {
    expect(safeUrlTransform('javascript:alert(1)')).toBe('')
    expect(safeUrlTransform('JaVaScRiPt:alert(1)')).toBe('')
    expect(safeUrlTransform('data:text/html,<script>')).toBe('')
    expect(safeUrlTransform('vbscript:msgbox(1)')).toBe('')
  })

  it('blocks missing urls', () => {
    expect(safeUrlTransform('')).toBe('')
    expect(safeUrlTransform(null)).toBe('')
    expect(safeUrlTransform(undefined)).toBe('')
  })
})
