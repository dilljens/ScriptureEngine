import { describe, it, expect, vi, afterEach } from 'vitest'
import { chatStream } from '../api'

// Build a Response whose body streams SSE events (undici Response works in node).
function sseResponse(events) {
  const body = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('')
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

function installFetch(mockResponse) {
  const spy = vi.fn().mockResolvedValue(mockResponse)
  globalThis.fetch = spy
  return spy
}

function sseResponseWithoutTrailingNewline(events) {
  const body = events.map(e => `data: ${JSON.stringify(e)}`).join('\n')
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('chatStream SSE parsing', () => {
  it('dispatches thinking/text chunks and resolves on done', async () => {
    installFetch(sseResponse([
      { type: 'thinking', content: 'think' },
      { type: 'text', content: 'Hello' },
      { type: 'text', content: ' world' },
      { type: 'done', usage: { total_tokens: 5 }, cost: { total: 0.001 }, model: 'deepseek-v4-flash', tool_results: [] },
    ]))
    const onThinking = vi.fn()
    const onText = vi.fn()
    const onDone = vi.fn()
    const onError = vi.fn()

    const event = await chatStream([{ role: 'user', content: 'hi' }], { onThinking, onText, onDone, onError })

    expect(onThinking).toHaveBeenCalledWith('think')
    expect(onText.mock.calls.map(c => c[0]).join('')).toBe('Hello world')
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onDone.mock.calls[0][0].final_content).toBeUndefined() // absent unless backend sends it
    expect(onError).not.toHaveBeenCalled()
    expect(event.type).toBe('done')
  })

  it('passes through final_content/final_reasoning from done event', async () => {
    installFetch(sseResponse([
      { type: 'done', final_content: 'Full text', final_reasoning: 'thought', tool_results: [], usage: {}, cost: {}, model: 'm' },
    ]))
    const onDone = vi.fn()
    await chatStream([], { onDone })
    expect(onDone.mock.calls[0][0].final_content).toBe('Full text')
    expect(onDone.mock.calls[0][0].final_reasoning).toBe('thought')
  })

  it('calls onError and rejects on an SSE error event', async () => {
    installFetch(sseResponse([
      { type: 'error', message: 'Rate limit exceeded. Try again in a minute.' },
    ]))
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/Rate limit/)
    expect(onError).toHaveBeenCalledWith('Rate limit exceeded. Try again in a minute.')
  })

  it('handles legacy ok:false error envelopes', async () => {
    installFetch(sseResponse([
      { ok: false, error: 'DEEPSEEK_API_KEY not configured' },
    ]))
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/DEEPSEEK_API_KEY/)
    expect(onError).toHaveBeenCalledWith('DEEPSEEK_API_KEY not configured')
  })

  it('flushes a final done event without a trailing newline', async () => {
    installFetch(sseResponseWithoutTrailingNewline([
      { type: 'done', final_content: 'tail', tool_results: [], usage: {}, cost: {}, model: 'm' },
    ]))
    const onDone = vi.fn()
    await chatStream([], { onDone })
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ final_content: 'tail' }))
  })

  it('rejects on EOF without a terminal event instead of hanging', async () => {
    installFetch(sseResponse([
      { type: 'text', content: 'partial' },
    ]))
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow(/connection closed/)
    expect(onError).toHaveBeenCalledWith(expect.stringContaining('connection closed'))
  })

  it('rejects with AbortError when the signal aborts', async () => {
    const controller = new AbortController()
    const abortError = new DOMException('The operation was aborted.', 'AbortError')
    const spy = vi.fn().mockImplementation((_url, opts) => Promise.reject(abortError))
    globalThis.fetch = spy
    await expect(chatStream([], { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('calls onError and rejects on non-2xx response', async () => {
    installFetch(new Response('oops', { status: 500 }))
    const onError = vi.fn()
    await expect(chatStream([], { onError })).rejects.toThrow()
    expect(onError).toHaveBeenCalledWith('The server encountered an error. Please try again.')
  })

  it('ignores unknown event types (e.g. heartbeat)', async () => {
    installFetch(sseResponse([
      { type: 'heartbeat' },
      { type: 'text', content: 'ok' },
      { type: 'done', tool_results: [], usage: {}, cost: {}, model: 'm' },
    ]))
    const onText = vi.fn()
    const onError = vi.fn()
    await chatStream([], { onText, onError })
    expect(onText).toHaveBeenCalledWith('ok')
    expect(onError).not.toHaveBeenCalled()
  })
})
