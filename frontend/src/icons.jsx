// biome-ignore-all lint/a11y/noSvgWithoutTitle — decorative icons, parent buttons have title
/**
 * Inline SVG icon components — 16×16, currentColor, consistent style.
 * No external deps — all pure React + SVG.
 * Decorative — parent buttons carry title/aria-label.
 */
const SZ = 16
const PROPS = {
  width: SZ, height: SZ,
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  role: 'presentation',
}

export function ChevronLeft(props) {
  return <svg {...PROPS} {...props}><path d="M10 3L5 8l5 5" /></svg>
}
export function ChevronRight(props) {
  return <svg {...PROPS} {...props}><path d="M6 3l5 5-5 5" /></svg>
}
export function ChevronUp(props) {
  return <svg {...PROPS} {...props}><path d="M3 10l5-5 5 5" /></svg>
}
export function ChevronDown(props) {
  return <svg {...PROPS} {...props}><path d="M3 6l5 5 5-5" /></svg>
}
export function SearchIcon(props) {
  return <svg {...PROPS} {...props}>
    <circle cx={7} cy={7} r={4.5} />
    <path d="M10.5 10.5l3 3" />
  </svg>
}
export function ChatIcon(props) {
  return <svg {...PROPS} {...props}>
    <path d="M2 3a1 1 0 011-1h10a1 1 0 011 1v7a1 1 0 01-1 1H7l-3 3v-3H3a1 1 0 01-1-1V3z" />
  </svg>
}
export function GridIcon(props) {
  return <svg {...PROPS} {...props}>
    <rect x={2} y={2} width={5} height={5} rx={0.5} />
    <rect x={9} y={2} width={5} height={5} rx={0.5} />
    <rect x={2} y={9} width={5} height={5} rx={0.5} />
    <rect x={9} y={9} width={5} height={5} rx={0.5} />
  </svg>
}
export function SunIcon(props) {
  return <svg {...PROPS} {...props}>
    <circle cx={8} cy={8} r={3} />
    <path d="M8 2v1M8 13v1M2 8h1M13 8h1M3.5 3.5l.7.7M11.8 11.8l.7.7M3.5 12.5l.7-.7M11.8 4.2l.7-.7" />
  </svg>
}
export function MoonIcon(props) {
  return <svg {...PROPS} {...props}>
    <path d="M13.5 9A6 6 0 017 2.5 6 6 0 1014 9z" />
  </svg>
}
export function GearIcon(props) {
  return <svg {...PROPS} {...props}>
    <circle cx={8} cy={8} r={2.5} />
    <path d="M8 1.5v1M8 13.5v1M1.5 8h1M13.5 8h1M3.2 3.2l.7.7M12.1 12.1l.7.7M3.2 12.8l.7-.7M12.1 3.9l.7-.7" strokeWidth={1.2} />
  </svg>
}
export function CommandIcon(props) {
  return <svg {...PROPS} {...props}>
    <rect x={3} y={3} width={10} height={10} rx={1.5} />
    <path d="M6 6h4v4H6z" />
    <path d="M6 3v10M10 3v10" strokeWidth={1} />
  </svg>
}
export function LayersIcon(props) {
  return <svg {...PROPS} {...props}>
    <path d="M2 8l6 3 6-3M2 11l6 3 6-3M2 5l6-3 6 3" />
  </svg>
}
export function ClockIcon(props) {
  return <svg {...PROPS} {...props}>
    <circle cx={8} cy={8} r={6} />
    <path d="M8 4.5V8l2.5 1.5" />
  </svg>
}
export function TextSmallIcon(props) {
  return <svg {...PROPS} {...props}>
    <path d="M5 12l3-8 3 8M6 9.5h4" />
  </svg>
}
export function TextLargeIcon(props) {
  return <svg {...PROPS} {...props}>
    <path d="M3.5 13l4.5-11 4.5 11M5 10h6" />
  </svg>
}
export function GraphIcon(props) {
  return <svg {...PROPS} {...props}>
    <circle cx={5} cy={5} r={1.5} />
    <circle cx={11} cy={5} r={1.5} />
    <circle cx={8} cy={11} r={1.5} />
    <path d="M6.5 6l1.5 3.5" />
    <path d="M9.5 6l-1.5 3.5" />
    <path d="M6.5 5h3" />
  </svg>
}

export function MemorizeIcon(props) {
  return <svg {...PROPS} {...props} width={16} height={16} viewBox="0 0 16 16">
    <path d="M2 3.5A1.5 1.5 0 013.5 2h9A1.5 1.5 0 0114 3.5v9a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 12.5v-9z" />
    <path d="M5.5 4.5v7M8 4.5v7M10.5 4.5v3" />
  </svg>
}

export function BookIcon(props) {
  return <svg {...PROPS} {...props}>
    <path d="M2 2.5l6 2v10l-6-2v-10z" />
    <path d="M14 2.5l-6 2v10l6-2v-10z" />
    <path d="M8 4.5v10" />
  </svg>
}

export function LibraryIcon(props) {
  return <svg {...PROPS} {...props}>
    <rect x={2} y={3} width={5} height={10} rx={0.5} />
    <rect x={9} y={3} width={5} height={10} rx={0.5} />
    <path d="M2 3l5 2M9 3l5 2" strokeWidth={1} />
  </svg>
}

export function TilesIcon(props) {
  return <svg {...PROPS} {...props}>
    <rect x={2} y={2} width={5} height={5} rx={1} />
    <rect x={9} y={2} width={5} height={5} rx={1} />
    <rect x={2} y={9} width={5} height={5} rx={1} />
    <rect x={9} y={9} width={5} height={5} rx={1} />
  </svg>
}

export function MenuIcon(props) {
  return <svg {...PROPS} {...props}>
    <line x1={2} y1={4} x2={14} y2={4} />
    <line x1={2} y1={8} x2={14} y2={8} />
    <line x1={2} y1={12} x2={14} y2={12} />
  </svg>
}

export function PlusIcon(props) {
  return <svg {...PROPS} {...props}>
    <line x1={8} y1={3} x2={8} y2={13} />
    <line x1={3} y1={8} x2={13} y2={8} />
  </svg>
}
