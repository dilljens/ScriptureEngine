/**
 * KnowledgeGraphView — Interactive knowledge graph for scripture connections.
 * Uses Cytoscape.js for force-directed layout with typed, colored, filterable edges.
 * Supports verses, TG topic nodes, and Bible Dictionary entries.
 *
 * API: GET /api/v1/graph/explore?verse=X&depth=N&layers=A,B&min_quality=N
 *      GET /api/v1/graph/search?q=X
 *      GET /api/v1/graph/centrality
 */
import React, { useEffect, useRef, useState, useCallback } from 'react'
import cytoscape from 'cytoscape'

// ── Layer color mapping (matches graph.py LAYER_CONFIG) ──
const LAYER_COLORS = {
  linguistic:    '#3b82f6',
  intertextual:  '#10b981',
  numerical:     '#f59e0b',
  structural:    '#8b5cf6',
  interpretive:  '#ec4899',
  symbolic:      '#06b6d4',
  textual:       '#84cc16',
  geographic:    '#f97316',
  chronological: '#a855f7',
  frequency:     '#64748b',
  sod:           '#dc2626',
}
const ALL_LAYERS = Object.keys(LAYER_COLORS)
const DEFAULT_EDGE_COLOR = '#6b7280'

// ── Node type styling ──
const NODE_TYPES = {
  verse:    { shape: 'ellipse',   color: '#6366f1', label: 'Verse' },
  topic:    { shape: 'diamond',   color: '#ef4444', label: 'TG Topic' },
  bd_entry: { shape: 'round-rectangle', color: '#3b82f6', label: 'Bible Dictionary' },
  unknown:  { shape: 'ellipse',   color: '#9ca3af', label: 'Unknown' },
}

function fmtNodeId(id) {
  if (id?.startsWith('tg:')) return id.slice(3).replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  if (id?.startsWith('bd:')) return `📖 ${id.slice(3).replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}`
  return id || ''
}

function shortenRef(ref) {
  if (!ref) return ''
  const parts = ref.split('.')
  if (parts.length === 3) return `${parts[0]}.${parts[2]}`
  return ref
}

export default function KnowledgeGraphView({ centerVerse, onNavigate, onOpenTab }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [depth, setDepth] = useState(1)
  const [activeLayers, setActiveLayers] = useState(new Set(ALL_LAYERS))
  const [minQuality, setMinQuality] = useState(0)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [hoveredEdge, setHoveredEdge] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState(null)

  // ── Fetch graph data ──
  const fetchGraph = useCallback(async (verse, d, layers, quality) => {
    setLoading(true)
    setError(null)
    try {
      const layerStr = [...activeLayers].join(',')
      const res = await fetch(`/api/v1/graph/explore?verse=${encodeURIComponent(verse)}&depth=${d}&layers=${layerStr}&min_quality=${quality}&limit=150`)
      const json = await res.json()
      if (json.ok) {
        setGraphData(json.data)
      } else {
        setError(json.detail || 'Failed to load graph')
      }
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }, [activeLayers])

  useEffect(() => {
    if (centerVerse) {
      fetchGraph(centerVerse, depth, activeLayers, minQuality)
    }
  }, [centerVerse, depth, fetchGraph, minQuality])

  // ── Search autocomplete ──
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/v1/graph/search?q=${encodeURIComponent(searchQuery)}&limit=10`)
        const json = await res.json()
        if (json.ok) setSearchResults(json.data.results)
      } catch {}
    }, 200)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // ── Build cytoscape elements ──
  const buildElements = useCallback((data) => {
    if (!data?.nodes?.length) return []
    const elements = []
    const seen = new Set()

    for (const node of data.nodes) {
      if (seen.has(node.id)) continue
      seen.add(node.id)
      const nt = NODE_TYPES[node.type] || NODE_TYPES.unknown
      elements.push({
        data: {
          id: node.id,
          label: node.type === 'verse' ? shortenRef(node.id) : fmtNodeId(node.id),
          ref: node.id,
          nodeType: node.type,
          nodeSubtype: node.subtype || '',
          title: node.title || node.id,
          description: node.description || '',
          size: node.size || 10,
          depth: node.depth || 0,
          connectionCount: node.connection_count || node.verse_count || 0,
          shape: nt.shape,
          nodeColor: nt.color,
        },
      })
    }

    for (const edge of data.edges) {
      if (!seen.has(edge.source) || !seen.has(edge.target)) continue
      elements.push({
        data: {
          id: `${edge.source}→${edge.target}-${edge.type}`,
          source: edge.source,
          target: edge.target,
          layer: edge.layer || 'unknown',
          type: edge.type || '',
          strength: edge.strength || 0.5,
          confidence: edge.confidence || 0.5,
          quality: edge.quality || 'suggested',
          label: '',
        },
      })
    }

    return elements
  }, [])

  // ── Initialize / update cytoscape ──
  useEffect(() => {
    if (!graphData || !containerRef.current) return

    const elements = buildElements(graphData)
    if (elements.length === 0) return

    // Destroy previous
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
            'font-size': 'mapData(connectionCount, 0, 100, 8, 13)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 2,
            'color': '#525252',
            'background-color': '#d4d4d4',
            'width': 'mapData(size, 5, 30, 16, 60)',
            'height': 'mapData(size, 5, 30, 16, 60)',
            'border-width': 2,
            'border-color': '#a3a3a3',
            'shape': 'data(shape)',
            'transition-property': 'background-color, border-color, opacity',
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
            'arrow-scale': 0.5,
            'transition-property': 'line-color, width, opacity',
            'transition-duration': 150,
          },
        },
        {
          selector: 'edge:selected',
          style: { 'line-color': '#f59e0b', 'width': 3 },
        },
        {
          selector: 'node[?depth=0]',
          style: {
            'border-width': 3,
            'border-color': '#3b82f6',
            'background-color': '#eff6ff',
            'font-weight': 'bold',
            'font-size': 12,
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
        padding: 30,
        nodeRepulsion: () => 12000,
        idealEdgeLength: () => 150,
        componentSpacing: 100,
        gravity: 0.25,
      },
      wheelSensitivity: 0.3,
      minZoom: 0.2,
      maxZoom: 5,
    })

    // Apply node type-based styling
    for (const node of cy.nodes()) {
      const nt = node.data('nodeType')
      const config = NODE_TYPES[nt] || NODE_TYPES.unknown
      const c = config.color
      const isRoot = node.data('depth') === 0
      node.style('background-color', isRoot ? '#eff6ff' : `${c}22`)
      node.style('border-color', isRoot ? '#3b82f6' : c)
      node.style('color', c)
      node.style('shape', config.shape)
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
      setHoveredNode({
        ref: n.data('ref'),
        label: n.data('title') || n.data('label'),
        nodeType: n.data('nodeType'),
        degree: n.degree(),
        connectionCount: n.data('connectionCount'),
        description: n.data('description'),
      })
      n.style('border-width', 4)
      n.connectedEdges().forEach(e => e.style('width', 3))
    })
    cy.on('mouseout', 'node', (evt) => {
      const n = evt.target
      setHoveredNode(null)
      n.style('border-width', n.data('depth') === 0 ? 3 : 2)
      n.connectedEdges().forEach(e => e.style('width', 1.5))
    })
    cy.on('mouseover', 'edge', (evt) => {
      const e = evt.target
      const layerColor = LAYER_COLORS[e.data('layer')] || DEFAULT_EDGE_COLOR
      setHoveredEdge({
        layer: e.data('layer'),
        type: e.data('type'),
        strength: e.data('strength'),
        quality: e.data('quality'),
        source: e.data('source'),
        target: e.data('target'),
        tradition: e.data('tradition') || 'none',
        hermeneutic: e.data('hermeneutic') || 'linguistic',
      })
      e.style('width', 4)
      e.style('line-color', '#f59e0b')
    })
    cy.on('mouseout', 'edge', (evt) => {
      const e = evt.target
      setHoveredEdge(null)
      const layerColor = LAYER_COLORS[e.data('layer')] || DEFAULT_EDGE_COLOR
      e.style('width', 1.5)
      e.style('line-color', layerColor)
    })

    // Click node → expand/center
    cy.on('tap', 'node', (evt) => {
      const n = evt.target
      const ref = n.data('ref')
      if (!ref) return
      // If already center, navigate; else expand
      if (n.data('depth') === 0) {
        // Navigate to verse
        if (ref.startsWith('tg:')) {
          window.open(`/graph?verse=${ref}`, '_blank')
        } else if (ref.startsWith('bd:')) {
          window.open(`/graph?verse=${ref}`, '_blank')
        } else {
          const parts = ref.split('.')
          if (parts.length >= 2) onNavigate?.(parts[0], parseInt(parts[1]) || 1)
        }
      }
    })

    // Right-click context menu
    cy.on('cxttap', 'node', (evt) => {
      const n = evt.target
      const ref = n.data('ref')
      const pos = evt.renderedPosition || { x: 0, y: 0 }
      setContextMenu({ ref, nodeType: n.data('nodeType'), x: pos.x, y: pos.y, label: n.data('title') || n.data('label') })
    })
    cy.on('tap', () => setContextMenu(null))

    cyRef.current = cy

    cy.one('layoutstop', () => {
      cy.fit(undefined, 40)
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graphData, buildElements, onNavigate, onOpenTab])

  // ── Layer toggle ──
  const toggleLayer = (layer) => {
    setActiveLayers(prev => {
      const next = new Set(prev)
      if (next.has(layer)) next.delete(layer)
      else next.add(layer)
      return next
    })
  }

  // ── Handlers ──
  const handleSearchSelect = (result) => {
    setSearchOpen(false)
    setSearchQuery(result.title)
    // This would navigate the graph — for now, refetch with new center
    // In full version, update centerVerse prop
    if (onOpenTab) {
      if (result.type === 'verse') {
        const parts = result.id.split('.')
        if (parts.length >= 2) onOpenTab(parts[0], parseInt(parts[1]) || 1, { label: result.title })
      } else {
        window.open(`/graph?verse=${result.id}`, '_blank')
      }
    }
  }

  if (!centerVerse) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-neutral-400 dark:text-neutral-500">
        Enter a verse reference to explore its connections
      </div>
    )
  }

  const layerEntries = Object.entries(LAYER_COLORS)
  const connCount = graphData?.edges?.length || 0
  const nodeCount = graphData?.nodes?.length || 0

  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shrink-0 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setSearchOpen(true) }}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search verses, topics..."
            className="w-full px-3 py-1.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 focus:border-indigo-400 dark:focus:border-indigo-500 outline-none transition-all"
          />
          {searchOpen && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
              {searchResults.map(r => (
                <button key={r.id} onClick={() => handleSearchSelect(r)}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-700 border-b border-neutral-100 dark:border-neutral-700 last:border-0 cursor-pointer transition-colors">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">{r.title}</span>
                  <span className="ml-2 text-neutral-400 text-[10px]">{r.subtitle}</span>
                </button>
              ))}
            </div>
          )}
          {searchOpen && searchQuery.length >= 2 && searchResults.length === 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg z-50 p-3 text-xs text-neutral-400 text-center">
              No results
            </div>
          )}
        </div>

        {/* Depth control */}
        <div className="flex items-center gap-1 text-[10px] text-neutral-500 dark:text-neutral-400">
          <span>Depth:</span>
          {[1, 2, 3].map(d => (
            <button key={d} onClick={() => setDepth(d)}
              className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors cursor-pointer ${
                depth === d
                  ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                  : 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'
              }`}>{d}</button>
          ))}
        </div>

        {/* Fit button */}
        <button onClick={() => { if (cyRef.current) cyRef.current.fit(undefined, 40) }}
          className="px-2 py-1 text-[10px] text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded transition-colors cursor-pointer">
          Fit
        </button>

        {/* Refresh */}
        <button onClick={() => fetchGraph(centerVerse, depth, activeLayers, minQuality)}
          disabled={loading}
          className="px-2 py-1 text-[10px] text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded transition-colors cursor-pointer disabled:opacity-50">
          ⟳
        </button>
      </div>

      {/* Layer filter bar */}
      <div className="flex items-center gap-1.5 px-4 py-1.5 border-b border-neutral-100 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/50 shrink-0 flex-wrap">
        <span className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mr-1">Layers:</span>
        {layerEntries.map(([layer, color]) => {
          const isActive = activeLayers.has(layer)
          return (
            <button key={layer} onClick={() => toggleLayer(layer)}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                isActive ? 'text-white' : 'text-neutral-400 dark:text-neutral-500 opacity-60 hover:opacity-100'
              }`}
              style={{ backgroundColor: isActive ? color : 'transparent' }}>
              <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: isActive ? 'white' : color }} />
              {layer}
            </button>
          )
        })}
        <span className="text-[9px] text-neutral-300 dark:text-neutral-600 mx-1">|</span>
        <span className="text-[9px] text-neutral-400 dark:text-neutral-500">{nodeCount} nodes, {connCount} edges</span>
      </div>

      {/* Graph area */}
      <div className="flex-1 relative" style={{ minHeight: 400 }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-neutral-900/60 z-10">
            <div className="flex items-center gap-2 text-sm text-neutral-400">
              <div className="w-4 h-4 border-2 border-neutral-300 dark:border-neutral-600 border-t-blue-500 rounded-full animate-spin" />
              Loading graph...
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-sm text-red-500 bg-white/80 dark:bg-neutral-900/80 p-4 rounded-lg">Error: {error}</div>
          </div>
        )}
        <div ref={containerRef} className="absolute inset-0" />

        {/* Hover tooltip - node */}
        {hoveredNode && (
          <div className="absolute top-2 left-2 bg-white/95 dark:bg-neutral-800/95 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-lg px-3 py-2 text-xs shadow-lg pointer-events-none z-20 max-w-xs">
            <div className="font-medium text-neutral-800 dark:text-neutral-200">{hoveredNode.ref}</div>
            {hoveredNode.label !== hoveredNode.ref && (
              <div className="text-neutral-500 dark:text-neutral-400 mt-0.5">{hoveredNode.label}</div>
            )}
            <div className="flex items-center gap-2 mt-1 text-neutral-400">
              <span className="capitalize text-[10px] px-1 rounded bg-neutral-100 dark:bg-neutral-700">
                {hoveredNode.nodeType === 'topic' ? 'TG Topic' : hoveredNode.nodeType === 'bd_entry' ? 'Bible Dictionary' : hoveredNode.nodeType}
              </span>
              <span>{hoveredNode.degree} connections</span>
            </div>
            {hoveredNode.description && (
              <div className="text-neutral-400 dark:text-neutral-500 mt-1 text-[10px] line-clamp-2">{hoveredNode.description}</div>
            )}
          </div>
        )}

        {/* Hover tooltip - edge */}
        {hoveredEdge && (
          <div className="absolute top-2 right-2 bg-white/95 dark:bg-neutral-800/95 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-lg px-3 py-2 text-xs shadow-lg pointer-events-none z-20 max-w-xs">
            <div className="flex items-center gap-2">
              <span className="font-medium text-neutral-800 dark:text-neutral-200 capitalize">{hoveredEdge.layer}</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
                hoveredEdge.tradition === 'none' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' :
                hoveredEdge.tradition === 'jewish' ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400' :
                hoveredEdge.tradition === 'christian' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' :
                hoveredEdge.tradition === 'lds' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' :
                hoveredEdge.tradition === 'multiple' ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' :
                'bg-neutral-100 dark:bg-neutral-700 text-neutral-500'
              }`}>
                {hoveredEdge.tradition === 'none' ? '🔬 Text' :
                 hoveredEdge.tradition === 'jewish' ? '✡️ Jewish' :
                 hoveredEdge.tradition === 'christian' ? '✝️ Christian' :
                 hoveredEdge.tradition === 'lds' ? '📖 LDS' :
                 hoveredEdge.tradition === 'multiple' ? '🤝 Multiple' : hoveredEdge.tradition}
              </span>
            </div>
            <div className="text-neutral-500 dark:text-neutral-400 mt-1">{hoveredEdge.type?.replace(/_/g, ' ')}</div>
            <div className="text-neutral-400 dark:text-neutral-500 text-[10px] mt-0.5">
              {hoveredEdge.hermeneutic} · strength: {(hoveredEdge.strength * 100).toFixed(0)}% · quality: {hoveredEdge.quality}
            </div>
            <div className="text-neutral-400 dark:text-neutral-500 mt-0.5 text-[10px]">
              {hoveredEdge.source} → {hoveredEdge.target}
            </div>
          </div>
        )}

        {/* Context menu */}
        {contextMenu && (
          <div className="fixed z-50 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-xl py-1 text-xs"
            style={{ left: contextMenu.x, top: contextMenu.y }}>
            <div className="px-3 py-1.5 text-neutral-400 dark:text-neutral-500 font-medium border-b border-neutral-100 dark:border-neutral-700">
              {contextMenu.label}
            </div>
            {contextMenu.nodeType === 'verse' && (
              <>
                <button onClick={() => { setContextMenu(null); window.open(`/graph?verse=${contextMenu.ref}`, '_blank') }}
                  className="w-full text-left px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">🔍 Explore connections</button>
                <button onClick={() => { setContextMenu(null); const p = contextMenu.ref.split('.'); if (p.length >= 2) onNavigate?.(p[0], parseInt(p[1]) || 1) }}
                  className="w-full text-left px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">📖 Open verse</button>
              </>
            )}
            {contextMenu.nodeType === 'topic' && (
              <button onClick={() => { setContextMenu(null); window.open(`/graph?verse=${contextMenu.ref}`, '_blank') }}
                className="w-full text-left px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">🏷️ Explore TG topic</button>
            )}
            {contextMenu.nodeType === 'bd_entry' && (
              <button onClick={() => { setContextMenu(null); window.open(`/graph?verse=${contextMenu.ref}`, '_blank') }}
                className="w-full text-left px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">📚 Open BD entry</button>
            )}
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-2 left-2 bg-white/80 dark:bg-neutral-900/80 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-lg px-2.5 py-1.5 shadow-sm z-20">
          <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mb-1 uppercase tracking-wider">Node Types</div>
          {Object.entries(NODE_TYPES).map(([type, config]) => (
            <div key={type} className="flex items-center gap-1.5 text-[9px] text-neutral-500 dark:text-neutral-400 mb-0.5">
              <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ backgroundColor: `${config.color}44`, border: `1.5px solid ${config.color}` }} />
              {config.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
