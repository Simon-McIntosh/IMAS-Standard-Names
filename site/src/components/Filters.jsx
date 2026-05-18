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

// Faceted filter sidebar. Counts are computed over the full corpus
// (passed in as `allCounts`/`faceted`) so they stay stable as the user
// toggles filters — preventing the "no remaining options" trap.
export function Filters({ filters, setFilters, faceted, allCounts }) {
  const { CATEGORIES } = useData();
  const toggle = (k, v) => {
    const cur = new Set(filters[k]);
    if (cur.has(v)) cur.delete(v); else cur.add(v);
    setFilters({ ...filters, [k]: cur });
  };
  const totalActive = Object.values(filters).reduce((a, s) => a + s.size, 0);

  return (
    <aside className="filters">
      <div className="filters-head">
        <div className="filters-title">Filters</div>
        {totalActive > 0 && (
          <button
            className="filters-clear"
            onClick={() =>
              setFilters({
                category: new Set(),
                unit: new Set(),
                kind: new Set(),
                status: new Set(),
                ids: new Set(),
                system: new Set(),
              })
            }
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

      <FilterGroup title="Kind">
        {[
          ['base', 'Base quantity'],
          ['component', 'Vector component'],
          ['at_point', 'At a locus'],
          ['global', 'Global scalar'],
        ].map(([k, lbl]) => (
          <FilterRow
            key={k}
            label={lbl}
            count={faceted.kinds[k] ?? 0}
            checked={filters.kind.has(k)}
            onChange={() => toggle('kind', k)}
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Source status" defaultOpen={false}>
        {[
          ['composed', 'Composed'],
          ['attached', 'Attached'],
          ['skipped', 'Skipped'],
          ['vocab_gap', 'Vocab gap'],
        ].map(([s, lbl]) => (
          <FilterRow
            key={s}
            label={lbl}
            count={faceted.statuses[s] ?? 0}
            checked={filters.status.has(s)}
            onChange={() => toggle('status', s)}
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Source type" defaultOpen={false}>
        <FilterRow
          label="Data Dictionary"
          count={faceted.totalSources}
          checked={filters.system.has('dd')}
          onChange={() => toggle('system', 'dd')}
        />
        <FilterRow
          label="Experimental"
          count={0}
          checked={filters.system.has('exp')}
          onChange={() => toggle('system', 'exp')}
        />
        <FilterRow
          label="Facility"
          count={0}
          checked={filters.system.has('fac')}
          onChange={() => toggle('system', 'fac')}
        />
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
