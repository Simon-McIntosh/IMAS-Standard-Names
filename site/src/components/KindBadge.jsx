export const KIND_GLYPHS = {
  base:      { glyph: 'B', title: 'Base quantity' },
  component: { glyph: '⊥', title: 'Vector component' },
  at_point:  { glyph: '·', title: 'At a locus' },
  global:    { glyph: 'Σ', title: 'Global scalar' },
};

export function KindBadge({ kind }) {
  const k = KIND_GLYPHS[kind] || { glyph: '?', title: kind };
  return (
    <span className={`kind-badge kind-${kind}`} title={k.title}>
      {k.glyph}
    </span>
  );
}
