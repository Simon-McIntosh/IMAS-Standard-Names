import { useMemo } from 'react';
import { useData } from '../lib/data.js';
import { clusterKey, clusterDescriptor } from '../lib/indexes.js';

// Lineage map: every distinct cluster (category+group) rendered as a
// hand-drawn SVG "spoke" diagram. No Mermaid here — performance at 300+
// names is fine with plain SVG.
export function Map({ onSelect, activeCategory, setActiveCategory }) {
  const { NAMES, CATEGORIES } = useData();
  const clusters = useMemo(() => {
    const byKey = new Map();
    for (const n of NAMES) {
      const k = clusterKey(n);
      if (!byKey.has(k)) {
        byKey.set(k, { key: k, members: [], group: n.group, category: n.category });
      }
      byKey.get(k).members.push(n);
    }
    return [...byKey.values()]
      .map((c) => {
        const desc = clusterDescriptor(c.members, NAMES);
        const rootEntry = desc.real ? NAMES.find((n) => n.name === desc.root) : null;
        return { ...c, descriptor: desc, rootEntry };
      })
      .sort((a, b) => b.members.length - a.members.length);
  }, [NAMES]);

  const filtered = useMemo(() => {
    if (!activeCategory) return clusters;
    return clusters.filter((c) => c.category === activeCategory);
  }, [clusters, activeCategory]);

  return (
    <div className="map-view">
      <div className="map-head">
        <div className="map-title">
          <h2>Lineage map</h2>
          <p>
            Names organised by their natural concept — a base quantity and its
            vector components, or a locus and all the quantities evaluated there.
            Click any name to open its definition.
          </p>
        </div>
        <div className="map-cats">
          <button
            className={!activeCategory ? 'on' : ''}
            onClick={() => setActiveCategory(null)}
          >
            All
          </button>
          {CATEGORIES.filter((c) => clusters.some((cl) => cl.category === c.id)).map((c) => (
            <button
              key={c.id}
              className={activeCategory === c.id ? 'on' : ''}
              onClick={() => setActiveCategory(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="map-grid">
        {filtered.map((c) => (
          <ClusterCard key={c.key} cluster={c} onSelect={onSelect} />
        ))}
      </div>

      <div className="map-meta">
        <span>
          {filtered.length} concepts ·{' '}
          {filtered.reduce((s, c) => s + c.members.length, 0)} names
        </span>
      </div>
    </div>
  );
}

function ClusterCard({ cluster, onSelect }) {
  const { CATEGORIES } = useData();
  const W = 320;
  const H = 220;
  const cx = W / 2;
  const cy = H / 2;
  const r = 70;
  const { descriptor, members, rootEntry } = cluster;
  const isRootInCatalog = !!rootEntry;
  const rootSpoke =
    descriptor.kind === 'locus' ? '@' : descriptor.kind === 'base' ? 'B' : '·';

  const orbit = members.filter((m) => m.name !== descriptor.root);
  const pts = orbit.map((m, i) => {
    const angle = -Math.PI / 2 + (i / Math.max(1, orbit.length)) * (Math.PI * 2);
    return { m, x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
  });

  const catColor = (id) => {
    const i = CATEGORIES.findIndex((c) => c.id === id);
    const hue = (i * 31) % 360;
    return `oklch(0.55 0.13 ${hue})`;
  };

  return (
    <div className="cluster-card">
      <div className="cluster-head">
        <span className={`cluster-kind cluster-kind-${descriptor.kind}`}>
          {descriptor.kind === 'locus'
            ? '@ locus'
            : descriptor.kind === 'base'
            ? 'base'
            : 'concept'}
        </span>
        <button
          className="cluster-root mono"
          disabled={!isRootInCatalog}
          onClick={() => isRootInCatalog && onSelect(descriptor.root)}
          title={
            isRootInCatalog
              ? `Open ${descriptor.root}`
              : 'Concept root — not itself a catalog entry'
          }
        >
          {descriptor.root}
        </button>
        <span className="cluster-count">{members.length}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="cluster-svg">
        {pts.map((p, i) => (
          <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} className="cluster-edge" />
        ))}
        <circle
          cx={cx}
          cy={cy}
          r="22"
          className={`cluster-rootnode ${isRootInCatalog ? 'real' : 'virtual'}`}
        />
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          className={`cluster-rootlabel ${isRootInCatalog ? '' : 'virtual'}`}
        >
          {rootSpoke}
        </text>
        {pts.map((p, i) => (
          <g
            key={i}
            transform={`translate(${p.x}, ${p.y})`}
            className="cluster-node"
            onClick={() => onSelect(p.m.name)}
          >
            <circle r="11" fill={catColor(p.m.category)} />
            <title>
              {p.m.name} · {p.m.unit || '1'} · {p.m.kind}
            </title>
          </g>
        ))}
      </svg>
      <div className="cluster-list">
        {orbit.slice(0, 5).map((m) => (
          <button
            key={m.name}
            className="cluster-item"
            onClick={() => onSelect(m.name)}
            title={m.short}
          >
            <span className="cluster-dot" style={{ background: catColor(m.category) }} />
            <span className="mono">{m.name}</span>
          </button>
        ))}
        {orbit.length > 5 && <div className="cluster-more">+{orbit.length - 5} more</div>}
      </div>
    </div>
  );
}
