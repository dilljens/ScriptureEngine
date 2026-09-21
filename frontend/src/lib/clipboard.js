/**
 * Clipboard copy that survives mobile browsers.
 *
 * navigator.clipboard.writeText() must be *called* inside the tap gesture —
 * after an await (e.g. a share POST) iOS rejects it with NotAllowedError.
 * Call this from the gesture when possible; otherwise it falls back to the
 * legacy execCommand path. Returns true when the text is on the clipboard.
 */
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {}
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.cssText = 'position:fixed;opacity:0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    const ok = document.execCommand('copy')
    ta.remove()
    return ok
  } catch {
    return false
  }
}
