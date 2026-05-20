import { useMemo } from 'react';
import { useData } from '../lib/data.js';
import { KindBadge } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';

// Middle pane: filtered, optionally-grouped list of result rows.
//
// Group modes:
//  - "none"     — flat, single empty-headed group, in the order `results`
//                 arrived (search-mode preserves score order)
//  - "category" — group by category label, alpha within
//  - "cluster"  — group by "${category} · ${group}"; within a category,
//                 bigger clusters first then alpha by key
//
// Score-ordered override:
//  When `searchMode === 'scored'`, the user has asked a question and
//  expects the most relevant hit at the top. Re-grouping into clusters
//  and then sorting each group alphabetically destroys that — typing
//  "pressure" then putting the result list into the Equilibrium cluster
//  buries every `*_pressure` row under `area_of_flux_surface` because
//  "a…" comes before "e…", and you see a row that only mentions
//  pressure in its long description above the row that IS pressure.
//  In score mode we therefore render the flat ordered list regardless
//  of `groupBy`. The toggle still shows the user's preferred grouping
//  for when they clear the query.
export function ResultsList({
  results,
  selected,
  onSelect,
  dense,
  groupBy,
  setGroupBy,
  query,
  searchTokens,
  searchMode,
}) {
  const { CATEGORIES } = useData();
  const scoreOrdered = searchMode === 'scored';
  const grouped = useMemo(() => {
    if (scoreOrdered || groupBy === 'none') return [['', results]];
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
  }, [results, groupBy, CATEGORIES, scoreOrdered]);

  const hasQuery = searchTokens && searchTokens.length > 0;

  return (
    <div className={`results-list dense-${dense}`}>
      {searchMode === 'fuzzy' && (
        <div className="results-fuzzy" title="No exact matches — showing subsequence matches against name">
          Fuzzy matches:
        </div>
      )}
      <div className="results-meta">
        <span>
          <strong>{results.length}</strong> {results.length === 1 ? 'name' : 'names'}
          {scoreOrdered && (
            <span className="results-sort-by" title="Sorted by search relevance — clear the query to re-enable grouping">
              {' · sorted by relevance'}
            </span>
          )}
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
              <KindBadge name={n} />
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
          <div>
            {hasQuery ? (
              <>No matches for «{query}»</>
            ) : (
              <>No names match these filters.</>
            )}
          </div>
          {hasQuery && (
            <div className="empty-tokens" aria-label="Parsed search tokens">
              <span className="empty-tokens-label">tokens parsed:</span>
              {searchTokens.map((t) => (
                <span key={t} className="empty-token mono">{t}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
