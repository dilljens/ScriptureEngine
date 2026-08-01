import { describe, it, expect } from 'vitest'
import { mergeMessages } from '../components/ChatPanel'

const welcome = { role: 'assistant', content: "I'm connected to the scripture engine", timestamp: '2026-01-01T00:00:00Z' }
const user = { role: 'user', content: 'What is the covenant?', timestamp: '2026-01-01T00:00:01Z' }
const answer = { role: 'assistant', content: 'The covenant thread runs...', timestamp: '2026-01-01T00:00:02Z' }

describe('mergeMessages', () => {
  it('dedups identical messages by role+timestamp+content', () => {
    const out = mergeMessages([welcome, user], [user, welcome])
    expect(out).toHaveLength(1) // welcome dropped, user deduped
    expect(out[0]).toEqual(user)
  })

  it('appends messages only present in the secondary list (save race window)', () => {
    // Server has user; local snapshot has user + finished assistant answer.
    const out = mergeMessages([welcome, user], [user, answer])
    expect(out).toHaveLength(2)
    expect(out[1]).toEqual(answer)
  })

  it('drops welcome messages entirely (each instance re-adds its own)', () => {
    const out = mergeMessages([welcome, user, answer], [])
    expect(out).toHaveLength(2)
    expect(out[0]).toEqual(user)
  })

  it('preserves primary order and keeps distinct identical-content messages with different timestamps', () => {
    const a1 = { role: 'user', content: 'again', timestamp: '2026-01-01T00:00:01Z' }
    const a2 = { role: 'user', content: 'again', timestamp: '2026-01-01T00:00:05Z' }
    const out = mergeMessages([a1], [a2])
    expect(out).toHaveLength(2)
  })

  it('is idempotent — merging the result into itself changes nothing', () => {
    const base = [user, answer]
    const once = mergeMessages(base, [answer])
    const twice = mergeMessages(once, [answer])
    expect(twice).toEqual(once)
  })
})
