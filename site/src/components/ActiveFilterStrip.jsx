import React from 'react';

const FILTER_LABEL = {
  category:  'Domain',
  unit:      'Unit',
  kind:      'Kind',
  lifecycle: 'Lifecycle',
  base:      'Base',
  operator:  'Operator',
  reduction: 'Reduction',
  modifier:  'Modifier',
  axis:      'Axis',
  locus:     'Locus',
  subject:   'Subject',
};

export function ActiveFilterStrip({ filters, setFilters }) {
  if (!filters) return null;

  const pills = [];
  for (const [key, set] of Object.entries(filters)) {
    if (!(set instanceof Set) || set.size === 0) continue;
    const label = FILTER_LABEL[key] || key;
    for (const value of set) {
      pills.push({ key, value, label });
    }
  }

  if (pills.length === 0) return null;

  const removeOne = (key, value) => {
    setFilters((f) => {
      const cur = new Set(f[key] || []);
      cur.delete(value);
      return { ...f, [key]: cur };
    });
  };

  const clearAll = () => {
    setFilters((f) => {
      const next = { ...f };
      for (const k of Object.keys(next)) {
        if (next[k] instanceof Set) next[k] = new Set();
      }
      return next;
    });
  };

  return (
    <div className="active-filters" role="region" aria-label="Active filters">
      {pills.map(({ key, value, label }) => (
        <span key={`${key}::${value}`} className="active-filter-pill">
          <span className="active-filter-pill-k">{label}</span>
          <span className="active-filter-pill-v mono">{value}</span>
          <button
            type="button"
            className="active-filter-pill-x"
            onClick={() => removeOne(key, value)}
            aria-label={`Remove ${label} filter ${value}`}
            title={`Remove ${label} filter ${value}`}
          >
            ×
          </button>
        </span>
      ))}
      {pills.length >= 2 && (
        <button
          type="button"
          className="active-filters-clear"
          onClick={clearAll}
          title="Clear all filters"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
