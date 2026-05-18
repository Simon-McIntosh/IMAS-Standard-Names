import { useState } from 'react';
import { StatusDot, STATUS_META } from './StatusDot.jsx';

// Collapsible card grouping sources by IDS root. The path shown per row
// has the IDS prefix stripped because it's already in the group heading.
export function SourceGroup({ ids, items }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="source-group">
      <button className="source-group-head" onClick={() => setOpen(!open)}>
        <span className="caret">{open ? '▾' : '▸'}</span>
        <span className="source-type">DD</span>
        <span className="mono">{ids}</span>
        <span className="source-group-count">{items.length}</span>
      </button>
      {open && (
        <div className="source-group-body">
          {items.map((s, i) => (
            <div className="source-item" key={i}>
              <StatusDot status={s.status} />
              <span className="source-path mono">{s.path.slice(ids.length + 1)}</span>
              <span className="source-status">
                {STATUS_META[s.status]?.label || s.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
