/**
 * Group an ordered verse list into segments so consecutive highlighted
 * verses render as ONE block (a 7-8 range reads as a single passage,
 * not two cards). Non-highlighted verses pass through untouched.
 *
 * groupVerses(verses, isTarget) → [{ verses: [...], highlighted: bool }]
 */
export function groupVerses(verses, isTarget) {
  const segs = []
  for (const v of verses || []) {
    const hl = !!isTarget(v)
    const last = segs[segs.length - 1]
    if (last && last.highlighted === hl) last.verses.push(v)
    else segs.push({ verses: [v], highlighted: hl })
  }
  return segs
}
