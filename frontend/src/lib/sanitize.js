/**
 * Sanitization helpers for LLM-rendered chat content.
 *
 * Chat content is rendered through react-markdown with rehype-raw so the
 * trusted :verse[...] / :entity[...] spans become clickable chips. LLM output
 * is untrusted, so we:
 *
 *   1. escapeHtml() — neutralize ALL raw HTML the LLM writes BEFORE our
 *      preprocess step re-injects its own (already escaped) span tags.
 *      The scripture markers (:verse[gen.1.1], %%%CLICK:...%%% etc.) contain
 *      only [a-z0-9_.:-%] so escaping never touches them.
 *   2. safeUrlTransform() — pass as react-markdown's urlTransform to block
 *      javascript:/data:/vbscript: URLs in markdown links (rehype-raw is not
 *      involved there — markdown link syntax reaches the anchor directly).
 */

// Escape HTML special characters so any raw HTML renders as inert text.
// Runs BEFORE preprocessScripture so the trusted spans survive.
export function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// urlTransform for react-markdown: allow relative URLs, anchors, and
// http(s)/mailto only. Blocks javascript:, data:, vbscript:, etc.
export function safeUrlTransform(url) {
  if (!url) return ''
  const trimmed = String(url).trim()
  if (/^(https?:|mailto:|#|\/(?!\/))/i.test(trimmed)) return url
  return ''
}
