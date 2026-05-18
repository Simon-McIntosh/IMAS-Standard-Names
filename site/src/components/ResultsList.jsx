import { useMemo } from 'react';
import { useData } from '../lib/data.js';
import { KindBadge } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';

// Middle pane: filtered, optionally-grouped list of result rows.
//
// Group modes:
//  - "none"     — flat, single empty-headed group, alpha by name
//  - "category" — group by category label, alpha within
//  - "cluster"  — group by "${category} · ${group}"; within a category,
//                 bigger clusters first then alpha by key
export function ResultsList({ results, selected, onSelect, dense, groupBy, setGroupBy }) {
  const { CATEGORIES } = useData();
  const grouped = useMemo(() => {
    if (groupBy === 'none') return [['', results]];
    const catOf = (id) => CATEGORIES.find((c) => c.id === id)?.label || id;
    const map = new Map();
    for (const n of results) {
      const key =
        groupBy === 'category' ? catOf(n.category) : `${catOf(n.category)} · ${n.group}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(n);
    }
    const entries = [...map.entries()].map(([k, items]) => [
      k,
      items.slice().sort((a, b) => a.name.localeCompare(b.name)),
    ]);
    if (groupBy === 'cluster') {
      entries.sort((A, B) => {
        const [ka, ia] = A;
        const [kb, ib] = B;
        const catA = ka.split(' · ')[0];
        const catB = kb.split(' · ')[0];
        if (catA !== catB) return catA.localeCompare(catB);
        if (ib.length !== ia.length) return ib.length - ia.length;
        return ka.localeCompare(kb);
      });
    } else {
      entries.sort((A, B) => A[0].localeCompare(B[0]));
    }
    return entries;
  }, [results, groupBy, CATEGORIES]);

  return (
    <div className={`results-list dense-${dense}`}>
      <div className="results-meta">
        <span>
          <strong>{results.length}</strong> {results.length === 1 ? 'name' : 'names'}
        </span>
        <div className="group-toggle" role="group" aria-label="Group results">
          {[
            ['none', 'A–Z'],
            ['category', 'Domain'],
            ['cluster', 'Concept'],
          ].map(([v, label]) => (
            <button
              key={v}
              className={groupBy === v ? 'on' : ''}
              onClick={() => setGroupBy(v)}
              title={
                v === 'cluster'
                  ? 'Group by concept (locus or base quantity)'
                  : v === 'category'
                  ? 'Group by domain'
                  : 'Flat alphabetical'
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {grouped.map(([heading, items]) => (
        <div key={heading} className="result-group">
          {heading && (
            <div className="result-group-head">
              <span className="result-group-label">{heading}</span>
              <span className="result-group-count">{items.length}</span>
            </div>
          )}
          {items.map((n) => (
            <button
              key={n.name}
              className={`result-row ${selected === n.name ? 'selected' : ''}`}
              onClick={() => onSelect(n.name)}
            >
              <KindBadge kind={n.kind} />
              <div className="result-main">
                <div className="result-name">{n.name}</div>
                {dense !== 'dense' && <div className="result-desc">{n.short}</div>}
              </div>
              <div className="result-meta">
                <UnitPill unit={n.unit} />
                <span className="result-sources">{n.sources.length}</span>
              </div>
            </button>
          ))}
        </div>
      ))}
      {results.length === 0 && (
        <div className="empty">
          <div className="empty-glyph">∅</div>
          <div>No names match these filters.</div>
        </div>
      )}
    </div>
  );
}
