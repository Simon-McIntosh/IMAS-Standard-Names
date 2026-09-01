// Five canonical schema kinds from entry_schema.json: scalar / vector
// / tensor / complex / metadata. Each glyph is a 16×16 SVG using
// currentColor; the badge class supplies hue + background via the
// .kind-{value} CSS classes.
//
//   scalar   — filled disc            (one value, unmarked)
//   vector   — single right-arrow     (magnitude + direction)
//   tensor   — 2×2 dot grid           (implicit row/column indices)
//   complex  — half-filled ring       (real + imaginary parts)
//   metadata — [·] bracket-bullet     (named anchor, not measurable)
export const KIND_GLYPHS = {
  scalar: {
    title: 'Scalar',
    svg: (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="8" cy="8" r="3" fill="currentColor" />
      </svg>
    ),
  },
  vector: {
    title: 'Vector',
    svg: (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M3 8H13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <path d="M10 5L13 8L10 11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
    ),
  },
  tensor: {
    title: 'Tensor',
    svg: (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="5"  cy="5"  r="1.6" fill="currentColor" />
        <circle cx="11" cy="5"  r="1.6" fill="currentColor" />
        <circle cx="5"  cy="11" r="1.6" fill="currentColor" />
        <circle cx="11" cy="11" r="1.6" fill="currentColor" />
      </svg>
    ),
  },
  complex: {
    title: 'Complex',
    svg: (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M8 3A5 5 0 0 1 8 13Z" fill="currentColor" />
        <circle cx="8" cy="8" r="5" stroke="currentColor" strokeWidth="1.4" fill="none" />
      </svg>
    ),
  },
  metadata: {
    title: 'Metadata',
    svg: (
      <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M5 3H3V13H5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <path d="M11 3H13V13H11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <circle cx="8" cy="8" r="1.3" fill="currentColor" />
      </svg>
    ),
  },
};

// Map an entry record (or bare string) to a canonical schema kind.
// Callers can pass either an explicit string or the record itself; the
// helper honours record.algebra first and falls back to "scalar".
export function schemaKindOf(n) {
  if (!n) return 'scalar';
  if (typeof n === 'string') return n;
  if (n.algebra) return n.algebra;
  return 'scalar';
}

// Single badge — one glyph per record, classed `.kind-{value}` so CSS
// can colour it. Accepts either `{ kind: 'vector' }`, `{ name: <record> }`,
// or a bare record (use `<KindBadge name={n} />`).
export function KindBadge({ kind, name }) {
  const sk = kind ? schemaKindOf(kind) : schemaKindOf(name);
  const g = KIND_GLYPHS[sk] || KIND_GLYPHS.scalar;
  return (
    <span className={`kind-badge kind-${sk}`} title={g.title}>
      {g.svg}
    </span>
  );
}

// Compact legend — render in the filter sidebar or empty-state.
export function KindLegend() {
  return (
    <div className="kind-legend">
      <div className="kind-legend-title">Kind legend</div>
      {Object.entries(KIND_GLYPHS).map(([k, { svg, title }]) => (
        <div key={k} className="kind-legend-row">
          <span className={`kind-badge kind-${k}`}>{svg}</span>
          <span>{title}</span>
        </div>
      ))}
    </div>
  );
}
