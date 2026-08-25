import { describe, it, expect, vi, afterEach } from 'vitest'
import { chatStream } from '../api'

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function installJobFetch(events, { status = 'done', error, done } = {}) {
  const responses = [
    jsonResponse({ ok: true, data: { job_id: 'job-1', seq: 0 } }),
    jsonResponse({ ok: true, data: { status, events, error, done } }),
  ]
  const spy = vi.fn().mockImplementation(() => Promise.resolve(responses.shift()))
  globalThis.fetch = spy
  return spy
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('chatStream background jobs', () => {
  it('dispatches thinking/text chunks and resolves on done', async () => {
    installJobFetch([
      { type: 'thinking', content: 'think' },
      { type: 'text', content: 'Hello' },
      { type: 'text', content: ' world' },
      { type: 'done', usage: { total_tokens: 5 }, cost: { total: 0.001 }, model: 'm', tool_results: [] },
    ])
    const onThinking = vi.fn()
    const onText = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    const event = await chatStream([{ role: 'user', content: 'hi' }], { onThinking, onText, onDone, onError })

    expect(onThinking).toHaveBeenCalledWith('think')
    expect(onText.mock.calls.map(c => c[0]).join('')).toBe('Hello world')
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onError).not.toHaveBeenCalled()
    expect(event.type).toBe('done')
  })

  it('passes through final_content/final_reasoning from done event', async () => {
    installJobFetch([
      { type: 'done', final_content: 'Full text', final_reasoning: 'thought', tool_results: [], usage: {}, cost: {}, model: 'm' },
    ])
    const onDone = vi.fn()
    await chatStream([], { onDone })
    expect(onDone.mock.calls[0][0].final_content).toBe('Full text')
    expect(onDone.mock.calls[0][0].final_reasoning).toBe('thought')
  })

  it('calls onError and rejects on a job error event', async () => {
    installJobFetch([{ type: 'error', message: 'Rate limit exceeded. Try again in a minute.' }])
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/Rate limit/)
    expect(onError).toHaveBeenCalledWith('Rate limit exceeded. Try again in a minute.')
  })

  it('handles legacy ok:false error envelopes', async () => {
    installJobFetch([{ ok: false, error: 'DEEPSEEK_API_KEY not configured' }])
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/DEEPSEEK_API_KEY/)
    expect(onError).toHaveBeenCalledWith('DEEPSEEK_API_KEY not configured')
  })

  it('rejects when a job terminates without a terminal event', async () => {
    installJobFetch([], { status: 'failed', error: 'connection closed' })
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/connection closed/)
    expect(onError).toHaveBeenCalledWith('connection closed')
  })

  it('rejects with AbortError when the signal aborts', async () => {
    const controller = new AbortController()
    const spy = vi.fn().mockImplementation((url) => {
      if (url.endsWith('/chat/jobs')) return Promise.resolve(jsonResponse({ ok: true, data: { job_id: 'job-1', seq: 0 } }))
      return new Promise(() => {})
    })
    globalThis.fetch = spy
    const promise = chatStream([], { signal: controller.signal })
    await Promise.resolve()
    controller.abort()
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('calls onError and rejects on non-2xx response', async () => {
    const spy = vi.fn().mockResolvedValue(new Response('oops', { status: 400 }))
    globalThis.fetch = spy
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/API 400/)
    expect(onError).toHaveBeenCalledWith(expect.stringContaining('API 400'))
  })

  it('ignores unknown event types such as heartbeat', async () => {
    installJobFetch([
      { type: 'heartbeat' },
      { type: 'text', content: 'ok' },
      { type: 'done', tool_results: [], usage: {}, cost: {}, model: 'm' },
    ])
    const onText = vi.fn()
    const onError = vi.fn()
    await chatStream([], { onText, onError })
    expect(onText).toHaveBeenCalledWith('ok')
    expect(onError).not.toHaveBeenCalled()
  })
})
