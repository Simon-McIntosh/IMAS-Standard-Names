import { useState } from 'react';
import { useData } from '../lib/data.js';

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

// Algebra (catalog `kind`) — rank/algebra of the quantity itself.
const ALGEBRA_ROWS = [
  ['scalar', 'Scalar'],
  ['vector', 'Vector'],
  ['tensor', 'Tensor'],
  ['complex', 'Complex'],
  ['metadata', 'Metadata'],
];

// Display kind (SPA's lineage-tree shape) — independent of algebra.
const DISPLAY_KIND_ROWS = [
  ['base', 'Base quantity'],
  ['component', 'Vector component'],
  ['at_point', 'At a locus'],
  ['global', 'Global scalar'],
  ['location', 'Location / metadata'],
];

// Catalog-level status (per ISN StandardNameStatus enum). Drawn from
// `n.status` directly, not aggregated over `n.sources[].status`.
const STATUS_ROWS = [
  ['published', 'Published'],
  ['drafted', 'Drafted'],
  ['draft', 'Draft (legacy)'],
  ['accepted', 'Accepted'],
  ['superseded', 'Superseded'],
  ['deprecated', 'Deprecated'],
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
  unit: new Set(),
  algebra: new Set(),
  display_kind: new Set(),
  status: new Set(),
  subject: new Set(),
  locus: new Set(),
  source_status: new Set(),
  ids: new Set(),
  system: new Set(),
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

  // Filter rows for closed-vocabulary axes only render if any data
  // points satisfy the value — avoids dead rows like "Tensor (0)".
  const nonEmpty = (counts) => (k) => (counts?.[k] ?? 0) > 0;

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

      <FilterGroup title="Algebra">
        {ALGEBRA_ROWS.filter(([k]) => nonEmpty(faceted.algebras)(k)).map(
          ([k, lbl]) => (
            <FilterRow
              key={k}
              label={lbl}
              count={faceted.algebras[k] ?? 0}
              checked={filters.algebra.has(k)}
              onChange={() => toggle('algebra', k)}
            />
          ),
        )}
      </FilterGroup>

      <FilterGroup title="Shape">
        {DISPLAY_KIND_ROWS.filter(([k]) =>
          nonEmpty(faceted.display_kinds)(k),
        ).map(([k, lbl]) => (
          <FilterRow
            key={k}
            label={lbl}
            count={faceted.display_kinds[k] ?? 0}
            checked={filters.display_kind.has(k)}
            onChange={() => toggle('display_kind', k)}
          />
        ))}
      </FilterGroup>

      {faceted.subjects.length > 0 && (
        <FilterGroup title="Subject" defaultOpen={false}>
          {faceted.subjects.map(([s, n]) => (
            <FilterRow
              key={s}
              label={s.replace(/_/g, ' ')}
              count={n}
              checked={filters.subject.has(s)}
              onChange={() => toggle('subject', s)}
            />
          ))}
        </FilterGroup>
      )}

      {faceted.loci.length > 0 && (
        <FilterGroup title="Locus" defaultOpen={false}>
          {faceted.loci.map(([l, n]) => (
            <FilterRow
              key={l}
              label={l.replace(/_/g, ' ')}
              mono
              count={n}
              checked={filters.locus.has(l)}
              onChange={() => toggle('locus', l)}
            />
          ))}
        </FilterGroup>
      )}

      <FilterGroup title="Status" defaultOpen={false}>
        {STATUS_ROWS.filter(([k]) => nonEmpty(faceted.statuses)(k)).map(
          ([k, lbl]) => (
            <FilterRow
              key={k}
              label={lbl}
              count={faceted.statuses[k] ?? 0}
              checked={filters.status.has(k)}
              onChange={() => toggle('status', k)}
            />
          ),
        )}
      </FilterGroup>

      <FilterGroup title="Source status" defaultOpen={false}>
        {SOURCE_STATUS_ROWS.map(([s, lbl]) => (
          <FilterRow
            key={s}
            label={lbl}
            count={faceted.source_statuses[s] ?? 0}
            checked={filters.source_status.has(s)}
            onChange={() => toggle('source_status', s)}
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Source root" defaultOpen={false}>
        {faceted.idses.map(([id, n]) => (
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
