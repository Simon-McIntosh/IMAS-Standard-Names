import { useState } from 'react';
import { useData } from '../lib/data.js';
import { KindBadge } from './KindBadge.jsx';

function FilterGroup({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`filter-group ${open ? 'open' : ''}`}>
      <button className="filter-head" onClick={() => setOpen(!open)}>
        <span className="caret">{open ? '▾' : '▸'}</span>
        <span>{title}</span>
      </button>
      {open && <div className="filter-body">{children}</div>}
    </div>
  );
}

function FilterRow({ label, count, checked, onChange, mono }) {
  return (
    <label className={`filter-row ${checked ? 'checked' : ''}`}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className={`filter-label ${mono ? 'mono' : ''}`}>{label}</span>
      <span className="filter-count">{count}</span>
    </label>
  );
}

// Schema kinds — five canonical values from entry_schema.json.
const KIND_ROWS = [
  ['scalar',   'Scalar'],
  ['vector',   'Vector'],
  ['tensor',   'Tensor'],
  ['complex',  'Complex'],
  ['metadata', 'Metadata'],
];

// Source-side status (per-source ingestion lifecycle on `n.sources[].status`).
const SOURCE_STATUS_ROWS = [
  ['composed', 'Composed'],
  ['attached', 'Attached'],
  ['skipped', 'Skipped'],
  ['vocab_gap', 'Vocab gap'],
];

const EMPTY_FILTERS = {
  category: new Set(),
  kind: new Set(),
  unit: new Set(),
  source_status: new Set(),
  ids: new Set(),
};

export const DEFAULT_FILTERS = EMPTY_FILTERS;

// Faceted filter sidebar. Counts are computed over the full corpus
// (passed in as `allCounts`/`faceted`) so they stay stable as the user
// toggles filters — preventing the "no remaining options" trap.
export function Filters({ filters, setFilters, faceted, allCounts }) {
  const { CATEGORIES } = useData();
  const toggle = (k, v) => {
    const cur = new Set(filters[k]);
    if (cur.has(v)) cur.delete(v);
    else cur.add(v);
    setFilters({ ...filters, [k]: cur });
  };
  const totalActive = Object.values(filters).reduce(
    (a, s) => a + (s instanceof Set ? s.size : 0),
    0,
  );

  return (
    <aside className="filters">
      <div className="filters-head">
        <div className="filters-title">Filters</div>
        {totalActive > 0 && (
          <button
            className="filters-clear"
            onClick={() => setFilters({ ...EMPTY_FILTERS })}
          >
            Clear ({totalActive})
          </button>
        )}
      </div>

      <FilterGroup title="Domain">
        {CATEGORIES.map((c) => (
          <FilterRow
            key={c.id}
            label={c.label}
            count={allCounts.category[c.id] ?? 0}
            checked={filters.category.has(c.id)}
            onChange={() => toggle('category', c.id)}
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Kind">
        {KIND_ROWS.filter(([k]) => (faceted.kinds[k] ?? 0) > 0).map(([k, lbl]) => (
          <FilterRow
            key={k}
            label={
              <span className="filter-kind-row">
                <KindBadge kind={k} />
                <span>{lbl}</span>
              </span>
            }
            count={faceted.kinds[k] ?? 0}
            checked={filters.kind.has(k)}
            onChange={() => toggle('kind', k)}
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Unit">
        {faceted.units.map(([u, n]) => (
          <FilterRow
            key={u}
            label={u}
            mono
            count={n}
            checked={filters.unit.has(u)}
            onChange={() => toggle('unit', u)}
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Advanced" defaultOpen={false}>
        <div className="filter-subhead">Source ingestion status</div>
        {SOURCE_STATUS_ROWS
          .filter(([s]) => (faceted.source_statuses[s] ?? 0) > 0)
          .map(([s, lbl]) => (
            <FilterRow
              key={s}
              label={lbl}
              count={faceted.source_statuses[s] ?? 0}
              checked={filters.source_status.has(s)}
              onChange={() => toggle('source_status', s)}
            />
          ))}

        <div className="filter-subhead">Source root (IDS)</div>
        {faceted.idses.slice(0, 12).map(([id, n]) => (
          <FilterRow
            key={id}
            label={id}
            mono
            count={n}
            checked={filters.ids.has(id)}
            onChange={() => toggle('ids', id)}
          />
        ))}
      </FilterGroup>
    </aside>
  );
}
