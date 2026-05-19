// Display-kind glyph (lineage shape: base / component / at_point / global / location).
export const KIND_GLYPHS = {
  base:      { glyph: 'B', title: 'Base quantity' },
  component: { glyph: '⊥', title: 'Vector component' },
  at_point:  { glyph: '·', title: 'At a locus' },
  global:    { glyph: 'Σ', title: 'Global scalar' },
  location:  { glyph: '⌖', title: 'Location / metadata' },
};

// Algebraic-kind chip (catalog `kind`: scalar / vector / tensor / complex / metadata).
export const ALGEBRA_CHIPS = {
  scalar:   { letter: 'S', title: 'Scalar (rank-0)' },
  vector:   { letter: 'V', title: 'Vector (rank-1)' },
  tensor:   { letter: 'T', title: 'Tensor (rank-2+)' },
  complex:  { letter: 'C', title: 'Complex-valued' },
  metadata: { letter: 'M', title: 'Metadata (no unit)' },
};

export function KindBadge({ kind, algebra }) {
  const k = KIND_GLYPHS[kind] || { glyph: '?', title: kind };
  const a = algebra ? ALGEBRA_CHIPS[algebra] : null;
  return (
    <span className="kind-badge-group" title={`${k.title}${a ? ` · ${a.title}` : ''}`}>
      {a && (
        <span className={`algebra-chip algebra-${algebra}`} title={a.title}>
          {a.letter}
        </span>
      )}
      <span className={`kind-badge kind-${kind}`} title={k.title}>
        {k.glyph}
      </span>
    </span>
  );
}

// Compact legend — render in the filter sidebar or empty-state.
export function KindLegend() {
  return (
    <div className="kind-legend">
      <div className="kind-legend-title">Kind legend</div>
      <div className="kind-legend-section">Shape (display)</div>
      {Object.entries(KIND_GLYPHS).map(([k, { glyph, title }]) => (
        <div key={k} className="kind-legend-row">
          <span className={`kind-badge kind-${k}`}>{glyph}</span>
          <span>{title}</span>
        </div>
      ))}
      <div className="kind-legend-section">Algebra</div>
      {Object.entries(ALGEBRA_CHIPS).map(([k, { letter, title }]) => (
        <div key={k} className="kind-legend-row">
          <span className={`algebra-chip algebra-${k}`}>{letter}</span>
          <span>{title}</span>
        </div>
      ))}
    </div>
  );
}
