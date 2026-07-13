/**
 * Agent control hook — drives automated frontend testing via the agent API.
 *
 * Activated by adding `?agent=true` to the URL.
 * Polls GET /api/v1/agent/actions and dispatches navigation/toggle/chat actions.
 *
 * Includes a keepalive mechanism to prevent the session from timing out.
 */

import { useEffect, useRef } from 'react'

const POLL_INTERVAL = 2000
const KEEPALIVE_INTERVAL = 60000

export default function useAgentControl({ currentTab, toggles, navigate, openTab, toggleDispatch }) {
  const cursorRef = useRef(-1)
  const enabledRef = useRef(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('agent') !== 'true') return

    enabledRef.current = true
    if (import.meta.env.DEV) { console.log('[agent] Agent control enabled') }

    // Keepalive — report current state every 60s
    const keepalive = setInterval(async () => {
      try {
        await fetch('/api/v1/agent/state', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: window.location.href,
            tab: currentTab ? { book: currentTab.book, chapter: currentTab.chapter, view: currentTab.view } : null,
            time: Date.now(),
          }),
        })
      } catch {}
    }, KEEPALIVE_INTERVAL)

    // Poll for actions
    const poll = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/agent/actions?after=${cursorRef.current}`)
        const data = await res.json()
        if (!data.ok) return

        const actions = data.data?.actions || []
        for (const action of actions) {
          cursorRef.current = Math.max(cursorRef.current, action.id)
          executeAction(action)
        }
      } catch {}
    }, POLL_INTERVAL)

    return () => {
      clearInterval(poll)
      clearInterval(keepalive)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function executeAction(action) {
    const { action: type, ...params } = action

    switch (type) {
      case 'navigate':
        if (params.book && params.chapter) {
          navigate(params.book, parseInt(params.chapter))
        }
        break
      case 'openTab':
        if (params.book && params.chapter) {
          openTab(params.book, parseInt(params.chapter), params.options || {})
        }
        break
      case 'toggle':
        if (params.toggle) {
          toggleDispatch(params.toggle)
        }
        break
      case 'chat':
        // Open chat tab with optional initialMessage
        break
      case 'reload':
        window.location.reload()
        break
      default:
        if (import.meta.env.DEV) { console.log('[agent] Unknown action:', type, params) }
    }
  }
}
