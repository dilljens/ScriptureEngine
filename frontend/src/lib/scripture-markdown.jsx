/**
 * Scripture Markdown — unified custom syntax for scripture references.
 *
 * Provides:
 *   preprocess(text) — converts custom syntax to <span data-type=""> tags
 *   components — react-markdown components object for rendering those tags
 *
 * Syntax              → Renders as
 * ─────────────────────────────────────────────────────────────────
 * :verse[gen.1.1]     → clickable verse chip with preview
 * :entity[Abraham]    → wiki entity link
 * :entity[person.abraham]  → wiki entity link (with ID)
 * :gematria[יהוה=26]  → gematria value badge
 * :strong[H430]       → Strong's definition popup
 * :conn[gen.1.1↔john.1.1]  → connection badge
 */

import React from 'react'

// ── Inline patterns ──

const RULES = [
  {
    // :verse[gen.1.1] or :verse[gen.1.1-12]
    pattern: /:verse\[([a-z0-9_]+\.\d+(?:\.\d+(?:-\d+)?)?)\]/g,
    type: 'verse',
    attr: 'data-ref',
  },
  {
    // :entity[Abraham] or :entity[person.abraham]
    pattern: /:entity\[([^\]]+)\]/g,
    type: 'entity',
    attr: 'data-entity',
  },
  {
    // :gematria[יהוה=26]
    pattern: /:gematria\[([^\]]+)\]/g,
    type: 'gematria',
    attr: 'data-value',
  },
  {
    // :strong[H430] or :strong[H430/word]
    pattern: /:strong\[([A-Z]\d+(?:\/[^\]]+)?)\]/g,
    type: 'strong',
    attr: 'data-lemma',
  },
  {
    // :conn[gen.1.1↔john.1.1]
    pattern: /:conn\[([^\]]+)\]/g,
    type: 'conn',
    attr: 'data-conn',
  },
]

// Build a combined regex for detection
const ALL_PATTERNS = new RegExp(RULES.map(r => r.pattern.source).join('|'), 'g')

/**
 * Pre-process markdown text: convert custom :syntax[args] to <span data-type=""> tags.
 * Returns the processed string ready for react-markdown.
 */
export function preprocess(text) {
  if (!text) return text

  // Reset lastIndex on all rules
  ALL_PATTERNS.lastIndex = 0

  let result = ''
  let lastIndex = 0
  let match

  while ((match = ALL_PATTERNS.exec(text)) !== null) {
    // Add text before this match
    result += text.slice(lastIndex, match.index)

    // Determine which rule matched
    for (let i = 0; i < RULES.length; i++) {
      const val = match[i + 1]
      if (val !== undefined) {
        const r = RULES[i]
        // Escape the value for use in an attribute
        const escaped = val.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        result += `<span data-type="${r.type}" ${r.attr}="${escaped}">${escaped}</span>`
        break
      }
    }

    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  result += text.slice(lastIndex)
  return result
}

/**
 * Extract the value from a matched span's data attributes.
 */
function extractValue(node) {
  if (!node) return null
  // node.props contains the React props, including data-* attributes
  return (
    node.props?.['data-ref']
    || node.props?.['data-entity']
    || node.props?.['data-value']
    || node.props?.['data-lemma']
    || node.props?.['data-conn']
    || null
  )
}

/**
 * components — pass this as the `components` prop to ReactMarkdown.
 * It handles rendering of scripture custom spans and provides nice defaults
 * for standard markdown elements.
 *
 * @param {Object} options
 * @param {Function} options.onOpenVerse — called with (ref) when a verse chip is clicked
 * @param {Function} options.onOpenEntity — called with (entityId) when an entity link is clicked
 * @param {Object} options.customComponents — additional component overrides (merged in)
 */
export function createComponents(options = {}) {
  const { onOpenVerse, onOpenEntity, customComponents } = options

  const base = {
    // ── Scripture custom spans ──
    span: ({ className, children, ...props }) => {
      const type = props['data-type']
      if (!type) {
        // Standard span — render without className if not set
        return <span className={className}>{children}</span>
      }

      const value = extractValue({ props })

      switch (type) {
        case 'verse':
          return (
            <span
              onClick={(e) => {
                e.stopPropagation()
                if (onOpenVerse) onOpenVerse(value)
              }}
              className={`inline align-baseline font-medium cursor-pointer transition-colors
                text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline
                ${className || ''}`}
              title={`Click to view ${value}`}
            >
              {value}
            </span>
          )

        case 'entity':
          return (
            <span
              onClick={(e) => {
                e.stopPropagation()
                if (onOpenEntity) onOpenEntity(value)
              }}
              className={`inline align-baseline font-medium cursor-pointer transition-colors
                text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 hover:underline
                ${className || ''}`}
              title={`View wiki article: ${value}`}
            >
              {value}
            </span>
          )

        case 'gematria':
          return (
            <span
              className={`inline align-baseline font-mono text-xs cursor-help
                bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded
                ${className || ''}`}
              title={`Gematria: ${value}`}
            >
              {value}
            </span>
          )

        case 'strong':
          return (
            <span
              className={`inline align-baseline font-mono text-xs
                bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-1 py-0.5 rounded cursor-help
                ${className || ''}`}
              title={`Strong's: ${value}`}
            >
              {value.startsWith('H') ? 'ה' : 'λ'} {value}
            </span>
          )

        case 'conn':
          return (
            <span
              className={`inline align-baseline text-xs font-mono
                bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-1.5 py-0.5 rounded
                ${className || ''}`}
              title={`Connection: ${value}`}
            >
              ↔ {value}
            </span>
          )

        default:
          return <span className={className}>{children}</span>
      }
    },

    // ── Nice defaults for standard elements ──
    p: ({ children }) => (
      <p className="my-0.5 text-sm leading-relaxed break-words">{children}</p>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-neutral-900 dark:text-neutral-100">{children}</strong>
    ),
    em: ({ children }) => (
      <em className="italic text-neutral-700 dark:text-neutral-300">{children}</em>
    ),
    code: ({ className, children, ...props }) => {
      const isInline = !className
      return isInline ? (
        <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded text-[10px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700" {...props}>
          {children}
        </code>
      ) : (
        <pre className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-3 my-1.5 overflow-x-auto text-[11px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
          <code className={className} {...props}>{children}</code>
        </pre>
      )
    },
    blockquote: ({ children }) => (
      <blockquote className="border-l-3 border-indigo-300 dark:border-indigo-600 pl-3 py-1 my-1.5 text-neutral-700 dark:text-neutral-300 text-sm italic">
        {children}
      </blockquote>
    ),
    h3: ({ children }) => (
      <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mt-3 mb-1 first:mt-0 text-sm">{children}</h3>
    ),
    ul: ({ children }) => (
      <ul className="list-disc list-inside space-y-0.5 my-1.5 text-sm text-neutral-700 dark:text-neutral-300">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside space-y-0.5 my-1.5 text-sm text-neutral-700 dark:text-neutral-300">{children}</ol>
    ),
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer"
        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline hover:decoration-dotted">
        {children}
      </a>
    ),
    hr: () => <hr className="my-2 border-neutral-200 dark:border-neutral-700" />,
    table: ({ children }) => (
      <div className="overflow-x-auto my-3">
        <table className="w-full text-xs sm:text-sm border-collapse border border-neutral-300 dark:border-neutral-700 rounded-lg overflow-hidden">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-neutral-100 dark:bg-neutral-800 border-b-2 border-neutral-300 dark:border-neutral-700">
        {children}
      </thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
        {children}
      </tbody>
    ),
    tr: ({ children }) => (
      <tr className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-3 py-2 text-left font-semibold text-neutral-700 dark:text-neutral-300 text-[11px] uppercase tracking-wider">{children}</th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-2 text-neutral-600 dark:text-neutral-400 align-top leading-relaxed">{children}</td>
    ),
  }

  // Merge custom component overrides
  return customComponents ? { ...base, ...customComponents } : base
}
