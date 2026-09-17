import React, { useRef, useEffect } from 'react'
import { LETTERS } from '../lib/idle-game'

/**
 * GolemCanvas — the "Incremancer half" of the design: your letters become
 * visible autonomous servants that work the workshop.
 *
 * Agency, not decoration: golems do not just emit dots. They physically carry
 * an Ohr mote to the bank (top-right), which pulses on delivery. They also
 * react to the player — a correct answer makes the horde surge and glow; a
 * wrong answer dims them for a moment. No audio (by design).
 *
 * Pure canvas 2D, rAF-driven, no per-frame React state. Capped for mobile
 * battery, and reduced-motion aware.
 *
 * Props:
 *   owned:      {letterIndex: count}
 *   mastery:    {letterIndex: 0..1}
 *   prestigeTick: number — increments to trigger a crumble/reform flourish
 *   answerPulse: {n, correct} — n changes on each graded answer
 *   onTap:      (x, y) => void — manual tap, coords relative to the wrapper (px)
 */

const MAX_GOLEMS = 44
const MAX_MOTES = 26
// Perf (Track D1): small screens draw fewer golems (22) — same roster logic,
// half the sprites.
const smallScreen = () => typeof window !== 'undefined'
  && window.matchMedia && window.matchMedia('(max-width: 640px)').matches

export default function GolemCanvas({ owned = {}, mastery = {}, prestigeTick = 0, answerPulse = null, onTap = null }) {
  const canvasRef = useRef(null)
  const stateRef = useRef({
    golems: [], motes: [], rings: [], lastPrestige: prestigeTick, crumble: 0,
    lastPulse: answerPulse?.n ?? null, reactUntil: 0, reactGood: true,
  })
  const propsRef = useRef({ owned, mastery, prestigeTick, answerPulse })
  propsRef.current = { owned, mastery, prestigeTick, answerPulse }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const reduced = typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false

    let raf
    let w = 0, h = 0, dpr = 1
    let lastT = 0

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = Math.max(1, Math.floor(w * dpr))
      canvas.height = Math.max(1, Math.floor(h * dpr))
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const rand = (a, b) => a + Math.random() * (b - a)
    const bankX = () => w - 22
    const bankY = 18

    // roundRect fallback for older engines
    const rrect = (x, y, ww, hh, r) => {
      if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(x, y, ww, hh, r); return }
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.arcTo(x + ww, y, x + ww, y + hh, r)
      ctx.arcTo(x + ww, y + hh, x, y + hh, r)
      ctx.arcTo(x, y + hh, x, y, r)
      ctx.arcTo(x, y, x + ww, y, r)
      ctx.closePath()
    }

    const makeGolem = (letterIdx) => ({
      li: letterIdx,
      x: rand(20, Math.max(30, w - 20)),
      y: rand(30, Math.max(40, h - 12)),
      vx: rand(-6, 6),
      vy: rand(-3, 3),
      phase: rand(0, Math.PI * 2),
      carrying: false,
      emitAt: performance.now() + rand(600, 3000),
    })

    // Rebuild roster from owned counts (stable per letter: keep existing).
    const syncRoster = () => {
      const target = []
      const ownedMap = propsRef.current.owned || {}
      const cap = smallScreen() ? 22 : MAX_GOLEMS
      const indices = Object.keys(ownedMap).map(Number).sort((a, b) => a - b)
      for (const li of indices) {
        const n = Math.min(ownedMap[li] || 0, 6) // cap per-letter visual
        for (let k = 0; k < n && target.length < cap; k++) target.push(li)
      }
      const cur = stateRef.current.golems
      if (cur.length > target.length) cur.length = target.length
      for (let i = cur.length; i < target.length; i++) cur.push(makeGolem(target[i]))
      for (let i = 0; i < cur.length; i++) {
        if (cur[i].li !== target[i]) cur[i].li = target[i]
      }
    }

    const drawGolem = (g, t, surge) => {
      const m = propsRef.current.mastery?.[g.li] || 0
      const golden = m >= 0.8
      const bob = reduced ? 0 : Math.sin(t / 320 + g.phase) * 1.6
      const x = g.x, y = g.y + bob
      const scale = (0.7 + m * 0.5) * (surge ? 1.12 : 1)

      if (golden) {
        ctx.beginPath()
        ctx.arc(x, y - 12 * scale, 5 * scale + Math.sin(t / 200 + g.phase) * 0.8, 0, Math.PI * 2)
        ctx.fillStyle = surge ? 'rgba(251,191,36,0.4)' : 'rgba(251,191,36,0.22)'
        ctx.fill()
      }

      const bw = 7 * scale, bh = 9 * scale
      ctx.fillStyle = golden ? '#c9a227' : (surge ? '#c49a72' : '#b08968')
      rrect(x - bw / 2, y - bh / 2, bw, bh, 2)
      ctx.fill()

      ctx.fillStyle = golden ? '#e3c25a' : '#c9a27a'
      ctx.beginPath()
      ctx.arc(x, y - bh * 0.75, 3.6 * scale, 0, Math.PI * 2)
      ctx.fill()

      // The shem — letter on the forehead
      ctx.fillStyle = golden ? '#3b2f00' : '#3a2b1e'
      ctx.font = `${8 * scale}px serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(LETTERS[g.li] || 'א', x, y - bh * 0.75)
    }

    const startCarry = (g) => {
      if (stateRef.current.motes.length >= MAX_MOTES) return
      stateRef.current.motes.push({
        x: g.x, y: g.y - 9, sx: g.x, sy: g.y - 9,
        tx: bankX(), ty: bankY, t: 0, golem: g,
      })
      g.carrying = true
    }

    const tick = (t) => {
      const st = stateRef.current
      const pr = propsRef.current

      // Prestige crumble
      if (pr.prestigeTick !== st.lastPrestige) {
        st.lastPrestige = pr.prestigeTick
        st.crumble = 1
      }
      // Answer reaction
      const pulseN = pr.answerPulse?.n ?? null
      if (pulseN !== null && pulseN !== st.lastPulse) {
        st.lastPulse = pulseN
        st.reactUntil = reduced ? 0 : t + (pr.answerPulse.correct ? 700 : 900)
        st.reactGood = !!pr.answerPulse.correct
        if (!pr.answerPulse.correct) {
          // Wrong answer: a soft dim ring, never a punishment
          st.rings.push({ x: w / 2, y: h / 2, r: 8, max: Math.max(w, h) * 0.6, alpha: 0.25, color: '120,120,140' })
        }
      }
      syncRoster()
      ctx.clearRect(0, 0, w, h)

      const surging = t < st.reactUntil && st.reactGood
      const dimmed = t < st.reactUntil && !st.reactGood

      // Ground
      ctx.strokeStyle = 'rgba(120,90,60,0.15)'
      ctx.beginPath(); ctx.moveTo(0, h - 6); ctx.lineTo(w, h - 6); ctx.stroke()

      // The bank (destination of every carried mote)
      ctx.beginPath()
      ctx.arc(bankX(), bankY, 9, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(251,191,36,0.12)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(251,191,36,0.5)'
      ctx.lineWidth = 1
      ctx.stroke()
      ctx.fillStyle = 'rgba(251,191,36,0.85)'
      ctx.font = '10px serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('✨', bankX(), bankY)

      const dt = lastT ? Math.min(0.05, (t - lastT) / 1000) : 1 / 60
      lastT = t
      const speedK = surging ? 1.9 : 1

      for (const g of st.golems) {
        if (!reduced) {
          g.x += g.vx * dt * speedK
          g.y += g.vy * dt * speedK
          if (g.x < 12) { g.x = 12; g.vx = Math.abs(g.vx) }
          if (g.x > w - 12) { g.x = w - 12; g.vx = -Math.abs(g.vx) }
          if (g.y < 20) { g.y = 20; g.vy = Math.abs(g.vy) }
          if (g.y > h - 12) { g.y = h - 12; g.vy = -Math.abs(g.vy) }
          if (Math.random() < 0.01) { g.vx = rand(-8, 8); g.vy = rand(-4, 4) }
          if (t > g.emitAt && !g.carrying) { startCarry(g); g.emitAt = t + rand(900, 3600) }
        }
        ctx.globalAlpha = dimmed ? 0.55 : 1
        drawGolem(g, t, surging)
        ctx.globalAlpha = 1
      }

      // Motes carried to the bank
      for (let i = st.motes.length - 1; i >= 0; i--) {
        const mo = st.motes[i]
        mo.t = Math.min(1, mo.t + dt * 0.7)
        // ease-out toward bank, with a slight arc
        const e = 1 - Math.pow(1 - mo.t, 3)
        mo.x = mo.sx + (mo.tx - mo.sx) * e
        mo.y = mo.sy + (mo.ty - mo.sy) * e - Math.sin(Math.PI * mo.t) * 10
        if (mo.t >= 1) {
          st.rings.push({ x: bankX(), y: bankY, r: 6, max: 22, alpha: 0.5, color: '251,191,36' })
          if (mo.golem) mo.golem.carrying = false
          st.motes.splice(i, 1)
          continue
        }
        ctx.globalAlpha = 0.9
        ctx.fillStyle = '#fbbf24'
        ctx.beginPath(); ctx.arc(mo.x, mo.y, 2.2, 0, Math.PI * 2); ctx.fill()
        ctx.globalAlpha = 1
      }

      // Bank delivery rings
      for (let i = st.rings.length - 1; i >= 0; i--) {
        const r = st.rings[i]
        r.r += 40 * dt
        r.alpha -= dt * 0.9
        if (r.alpha <= 0 || r.r > r.max) { st.rings.splice(i, 1); continue }
        ctx.beginPath()
        ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(${r.color},${Math.max(0, r.alpha)})`
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      // Prestige crumble flash
      if (st.crumble > 0) {
        st.crumble -= dt * 0.8
        ctx.fillStyle = `rgba(255,255,255,${Math.max(0, st.crumble) * 0.5})`
        ctx.fillRect(0, 0, w, h)
      }

      raf = 0
      // Perf (Track D1): stop the loop when the tab is hidden or the canvas
      // scrolled offscreen; resume on visibility/intersection. Idle tabs go
      // from 60fps to zero.
      if (!document.hidden && onScreen) raf = requestAnimationFrame(tick)
    }
    let onScreen = true
    const kick = () => {
      if (!document.hidden && onScreen && !raf) { lastT = 0; raf = requestAnimationFrame(tick) }
    }
    const io = typeof IntersectionObserver !== 'undefined'
      ? new IntersectionObserver(([e]) => { onScreen = e.isIntersecting; kick() })
      : null
    if (io) io.observe(canvas)
    document.addEventListener('visibilitychange', kick)
    raf = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', kick)
      if (io) io.disconnect()
    }
  }, [])

  return (
    <div
      className={`relative mt-2 rounded-lg overflow-hidden border border-amber-200 dark:border-amber-800 bg-gradient-to-b from-amber-100/60 to-amber-50/30 dark:from-neutral-900 dark:to-neutral-800 ${onTap ? 'cursor-pointer active:scale-[0.995] select-none focus-visible:outline-2 focus-visible:outline-amber-500' : ''}`}
      onPointerDown={onTap ? (e) => {
        const r = e.currentTarget.getBoundingClientRect()
        onTap(e.clientX - r.left, e.clientY - r.top)
      } : undefined}
      role={onTap ? 'button' : undefined}
      tabIndex={onTap ? 0 : undefined}
      aria-label={onTap ? 'Tap golems for Ohr' : undefined}
      title={onTap ? 'Tap for Ohr ✨' : undefined}
      onKeyDown={onTap ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          const r = e.currentTarget.getBoundingClientRect()
          onTap(r.width / 2, r.height / 2)
        }
      } : undefined}
    >
      <canvas ref={canvasRef} className="w-full block h-[76px] sm:h-[108px] pointer-events-none" aria-hidden="true" />
      {Object.keys(owned || {}).length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-[11px] text-neutral-500 dark:text-neutral-400 pointer-events-none text-center px-4">
          Your workshop is empty — inscribe a letter below to raise your first golem 👇
        </div>
      )}
    </div>
  )
}
