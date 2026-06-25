/**
 * ConnectionGraph — interactive Obsidian-style connection graph for scripture.
 * Uses Cytoscape.js for force-directed layout with colored edges by layer.
 *
 * Props:
 *   centerVerse — verse reference to center the graph on (e.g. "isa.6.1")
 *   onNavigate(b, ch) — navigate current tab to a verse
 *   onOpenTab(b, ch, opts) — open a verse in a new tab
 */
import React, { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape from 'cytoscape'

// ── Layer color mapping ──
const LAYER_COLORS = {
  linguistic: '#10b981',
  numerical: '#f59e0b',
  structural: '#8b5cf6',
  intertextual: '#3b82f6',
  textual: '#ec4899',
  geographic: '#14b8a6',
  chronological: '#f97316',
  interpretive: '#a855f7',
  frequency: '#06b6d4',
  symbolic: '#eab308',
  sod: '#ef4444',
}
const DEFAULT_EDGE_COLOR = '#6b7280'

// ── Work colors for nodes ──
const WORK_COLORS = {
  ot: '#d97706',
  nt: '#2563eb',
  bom: '#16a34a',
  dc: '#7c3aed',
  pgp: '#db2777',
}

function guessWorkFromRef(ref) {
  const book = ref?.split('.')[0] || ''
  const ot = ['gen','exo','lev','num','deu','josh','judg','ruth','1sam','2sam','1kgs','2kgs','1chr','2chr','ezra','neh','esth','job','psa','prov','eccl','song','isa','jer','lam','ezek','dan','hos','joel','amos','obad','jonah','mic','nah','hab','zeph','hag','zech','mal']
  const nt = ['matt','mark','luke','john','acts','rom','1cor','2cor','gal','eph','phil','col','1thes','2thes','1tim','2tim','titus','philem','heb','james','1pet','2pet','1john','2john','3john','jude','rev']
  const bom = ['1ne','2ne','jacob','enos','jarom','omni','wom','mosiah','alma','hel','3ne','4ne','morm','ether','moro']
  const dc_prefixes = ['dc']
  if (ot.includes(book)) return 'ot'
  if (nt.includes(book)) return 'nt'
  if (bom.includes(book)) return 'bom'
  if (dc_prefixes.some(p => book.startsWith(p))) return 'dc'
  return 'pgp'
}

function shortenRef(ref) {
  if (!ref) return ''
  const parts = ref.split('.')
  if (parts.length === 3) return `${parts[0]}.${parts[2]}`
  return ref
}

export default function ConnectionGraph({ centerVerse, onNavigate, onOpenTab }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [depth, setDepth] = useState(1)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [hoveredEdge, setHoveredEdge] = useState(null)

  // Parse center verse
  const centerParts = centerVerse?.split('.') || []
  const centerBook = centerParts[0] || ''
  const centerChapter = parseInt(centerParts[1]) || 1

  // Fetch verse data
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        // Fetch the verse with connections
        const res = await fetch(`/api/v1/verses/${centerVerse}?show_signals=true`)
        const json = await res.json()
        if (!json.ok) throw new Error(json.error || 'Failed to load verse')
        setData(json.data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [centerVerse])

  // Build cytoscape elements from connection data
  const buildElements = useCallback((verseData) => {
    if (!verseData?.connections) return []
    const elements = []
    const seen = new Set()

    // Center node
    const centerId = verseData.verse_id || centerVerse
    const centerWork = guessWorkFromRef(centerId)
    elements.push({
      data: { id: centerId, label: shortenRef(centerId), ref: centerId, work: centerWork, isCenter: true },
    })
    seen.add(centerId)

    // Add connection edges and target nodes (limit to ~100 for performance)
    const conns = verseData.connections || {}
    let edgeCount = 0
    const MAX_EDGES = 100
    for (const [layer, items] of Object.entries(conns)) {
      if (!Array.isArray(items)) continue
      for (const item of items) {
        if (edgeCount >= MAX_EDGES) break
        // The target field can be 'target' or 'target_verse' depending on endpoint
        const target = item.target || item.target_verse
        if (!target) continue

        // Add target node if not seen
        if (!seen.has(target)) {
          const tw = guessWorkFromRef(target)
          elements.push({
            data: { id: target, label: shortenRef(target), ref: target, work: tw, isCenter: false },
          })
          seen.add(target)
        }

        // Add edge
        const edgeId = `${centerId}→${target}-${layer}-${item.type || ''}-${edgeCount}`
        elements.push({
          data: {
            id: edgeId,
            source: centerId,
            target,
            layer,
            type: item.type || '',
            confidence: item.confidence || item.strength || 0.5,
            label: `${layer}: ${item.type || ''}`,
          },
        })
        edgeCount++
      }
      if (edgeCount >= MAX_EDGES) break
    }

    // Truncate edgeCount info for display
    const totalConns = Object.values(conns).reduce((s, a) => s + (Array.isArray(a) ? a.length : 0), 0)
    if (edgeCount < totalConns) {
      elements._truncated = totalConns - edgeCount
    }

    return elements
  }, [centerVerse])

  // Initialize / update cytoscape
  useEffect(() => {
    if (!data || !containerRef.current) return

    const elements = buildElements(data)
    if (elements.length === 0) return

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy()
      cyRef.current = null
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'font-size': '10px',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 2,
            'color': '#525252',
            'background-color': '#d4d4d4',
            'width': 'mapData(degree, 0, 10, 16, 40)',
            'height': 'mapData(degree, 0, 10, 16, 40)',
            'border-width': 2,
            'border-color': '#a3a3a3',
            'transition-property': 'background-color, border-color',
            'transition-duration': 150,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#d4d4d4',
            'target-arrow-color': '#d4d4d4',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.6,
            'transition-property': 'line-color, width',
            'transition-duration': 150,
          },
        },
        {
          selector: 'node[isCenter]',
          style: {
            'border-width': 3,
            'border-color': '#3b82f6',
            'background-color': '#eff6ff',
            'font-weight': 'bold',
            'font-size': '11px',
          },
        },
        {
          selector: 'node[?isCenter]',
          style: { 'text-valign': 'center', 'text-margin-y': 0, 'text-halign': 'right', 'text-margin-x': -6 },
        },
        {
          selector: 'edge:selected',
          style: { 'line-color': '#f59e0b', 'width': 3 },
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
        padding: 30,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 120,
        componentSpacing: 100,
        gravity: 0.3,
      },
      wheelSensitivity: 0.3,
      minZoom: 0.3,
      maxZoom: 4,
    })

    // Apply work-based node colors
    for (const node of cy.nodes()) {
      const work = node.data('work')
      if (work && WORK_COLORS[work]) {
        const c = WORK_COLORS[work]
        node.style('background-color', `${c}22`)
        node.style('border-color', c)
        node.style('color', c)
      }
    }

    // Apply layer-based edge colors
    for (const edge of cy.edges()) {
      const layer = edge.data('layer')
      const layerColor = LAYER_COLORS[layer] || DEFAULT_EDGE_COLOR
      edge.style('line-color', layerColor)
      edge.style('target-arrow-color', layerColor)
    }

    // Hover events
    cy.on('mouseover', 'node', (evt) => {
      const n = evt.target
      setHoveredNode({ ref: n.data('ref'), label: n.data('label'), degree: n.degree() })
      n.style('border-width', 4)
      // Highlight connected edges
      n.connectedEdges().forEach(e => e.style('width', 3))
    })
    cy.on('mouseout', 'node', (evt) => {
      const n = evt.target
      setHoveredNode(null)
      n.style('border-width', n.data('isCenter') ? 3 : 2)
      n.connectedEdges().forEach(e => e.style('width', 1.5))
    })
    cy.on('mouseover', 'edge', (evt) => {
      const e = evt.target
      setHoveredEdge({ layer: e.data('layer'), type: e.data('type'), confidence: e.data('confidence') })
      e.style('width', 4)
    })
    cy.on('mouseout', 'edge', () => {
      setHoveredEdge(null)
    })

    // Click to navigate
    cy.on('tap', 'node', (evt) => {
      const n = evt.target
      const ref = n.data('ref')
      if (!ref) return
      const parts = ref.split('.')
      if (parts.length >= 2) {
        const b = parts[0]
        const ch = parseInt(parts[1]) || 1
        if (n.data('isCenter')) {
          onNavigate?.(b, ch)
        } else {
          onOpenTab?.(b, ch, { label: n.data('label') })
        }
      }
    })

    cyRef.current = cy

    // Fit to view after layout
    cy.one('layoutstop', () => {
      cy.fit(undefined, 40)
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [data, buildElements, onNavigate, onOpenTab])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-neutral-400 dark:text-neutral-500">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-neutral-300 dark:border-neutral-600 border-t-blue-500 rounded-full animate-spin" />
          Loading graph...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-red-500">
        Failed to load graph: {error}
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-neutral-400">
        No data for {centerVerse}
      </div>
    )
  }

  const connCount = Object.values(data.connections || {}).reduce((sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0), 0)
  const displayCount = Math.min(connCount, 100)

  return (
    <div className="flex-1 flex flex-col">
      {/* Info bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shrink-0">
        <div className="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
          <span><strong className="text-neutral-700 dark:text-neutral-300">{centerVerse}</strong> — {displayCount}/{connCount} connections</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span className="flex items-center gap-1">
            {Object.entries(LAYER_COLORS).map(([layer, color]) => (
              <span key={layer} className="inline-flex items-center gap-0.5">
                <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: color }} />
                <span className="text-[9px]">{layer}</span>
              </span>
            ))}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Depth control */}
          <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400">
            <span>Depth:</span>
            {[1, 2, 3].map(d => (
              <button key={d} onClick={() => setDepth(d)}
                className={`px-1.5 py-0.5 rounded text-xs font-medium transition-colors cursor-pointer ${
                  depth === d
                    ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                    : 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'
                }`}>{d}</button>
            ))}
          </div>
          <button onClick={() => {
            if (cyRef.current) cyRef.current.fit(undefined, 40)
          }} className="px-2 py-1 text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded transition-colors cursor-pointer">
            Fit
          </button>
        </div>
      </div>

      {/* Graph area */}
      <div className="flex-1 relative" style={{ minHeight: 400 }}>
        <div ref={containerRef} className="absolute inset-0" />

        {/* Hover tooltip */}
        {hoveredNode && (
          <div className="absolute top-2 left-2 bg-white/90 dark:bg-neutral-800/90 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-lg px-3 py-1.5 text-xs shadow-lg pointer-events-none z-10">
            <div className="font-medium text-neutral-800 dark:text-neutral-200">{hoveredNode.ref}</div>
            <div className="text-neutral-500 dark:text-neutral-400">{hoveredNode.degree} connections</div>
          </div>
        )}
        {hoveredEdge && (
          <div className="absolute top-2 right-2 bg-white/90 dark:bg-neutral-800/90 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-lg px-3 py-1.5 text-xs shadow-lg pointer-events-none z-10">
            <div className="font-medium text-neutral-800 dark:text-neutral-200 capitalize">{hoveredEdge.layer}</div>
            <div className="text-neutral-500 dark:text-neutral-400">{hoveredEdge.type}</div>
            <div className="text-neutral-500 dark:text-neutral-400">confidence: {(hoveredEdge.confidence * 100).toFixed(0)}%</div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-2 left-2 bg-white/80 dark:bg-neutral-900/80 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-lg px-2.5 py-1.5 shadow-sm">
          <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mb-1 uppercase tracking-wider">Work</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(WORK_COLORS).map(([work, color]) => (
              <span key={work} className="inline-flex items-center gap-1 text-[9px] text-neutral-500 dark:text-neutral-400">
                <span className="w-2 h-2 rounded inline-block" style={{ backgroundColor: color }} />
                {work.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
      </div>

    </div>
  )
}
