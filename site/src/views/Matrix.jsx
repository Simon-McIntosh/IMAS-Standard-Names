import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../lib/data.js';

const ROW_CAP = 20;
const COL_CAP = 14;

const MATRIX_COLS = [
  {
    id: 'axis', label: 'Axis', filterKey: 'axis',
    get: (n) => n.parse?.find((t) => t.role === 'axis')?.text || null,
  },
  {
    id: 'locus', label: 'Locus', filterKey: 'locus',
    get: (n) => n.parse?.find((t) => t.role === 'locus')?.text || null,
  },
  {
    id: 'operator', label: 'Operator', filterKey: 'operator',
    get: (n) => n.parse?.find((t) => t.role === 'operator')?.text || null,
  },
  {
    id: 'domain', label: 'Domain', filterKey: 'category',
    get: (n) => n.category || null,
  },
];

function rowBaseOf(n) {
  const baseTok = n.parse?.find((t) => t.role === 'base');
  if (baseTok?.text) return baseTok.text;
  if (n.parent) return n.parent;
  return n.name;
}

function topN(freqMap, cap) {
  return [...freqMap.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, cap)
    .map(([k]) => k);
}

export function VocabularyMatrix({ onSelect, setFilters, setView }) {
  const { NAMES } = useData();
  const [activeColId, setActiveColId] = useState(MATRIX_COLS[0].id);
  const [popover, setPopover] = useState(null);
  const popoverRef = useRef(null);

  const colDef = MATRIX_COLS.find((c) => c.id === activeColId) ?? MATRIX_COLS[0];

  const { rows, cols, cells } = useMemo(() => {
    const rowFreq = new Map();
    const colFreq = new Map();
    const cellMap = new Map();

    for (const n of NAMES) {
      const row = rowBaseOf(n);
      const col = colDef.get(n);
      if (!col) continue;
      rowFreq.set(row, (rowFreq.get(row) || 0) + 1);
      colFreq.set(col, (colFreq.get(col) || 0) + 1);
      const k = `${row}\x00${col}`;
      if (!cellMap.has(k)) cellMap.set(k, []);
      cellMap.get(k).push(n);
    }

    return {
      rows: topN(rowFreq, ROW_CAP),
      cols: topN(colFreq, COL_CAP),
      cells: cellMap,
    };
  }, [NAMES, colDef]);

  const totalWithCol = useMemo(
    () => NAMES.filter((n) => colDef.get(n)).length,
    [NAMES, colDef],
  );

  useEffect(() => {
    if (!popover) return;
    const onKey = (e) => { if (e.key === 'Escape') setPopover(null); };
    const onDown = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) setPopover(null);
    };
    window.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
    };
  }, [popover]);

  const handleRowClick = (row) => {
    setFilters((prev) => ({ ...prev, base: new Set([row]) }));
    setView('browse');
  };

  const handleColClick = (col) => {
    setFilters((prev) => ({ ...prev, [colDef.filterKey]: new Set([col]) }));
    setView('browse');
  };

  const handleCellClick = (row, col, e) => {
    const names = cells.get(`${row}\x00${col}`);
    if (!names?.length) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setPopover({ row, col, names, rect });
  };

  return (
    <div className="matrix-view" data-active-view="matrix">
      <div className="matrix-head">
        <div className="matrix-title">
          <h2>Vocabulary map</h2>
          <p>
            Base quantities (rows) × {colDef.label.toLowerCase()} values (columns).
            Click a filled cell to browse names at that intersection; click a row or column
            header to filter the catalog by that value.
          </p>
        </div>
        <div className="seg">
          {MATRIX_COLS.map((c) => (
            <button
              key={c.id}
              className={activeColId === c.id ? 'on' : ''}
              onClick={() => setActiveColId(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="matrix-scroll">
        <table className="matrix-table">
          <thead>
            <tr>
              <th className="matrix-corner" />
              {cols.map((col) => (
                <th key={col} className="matrix-col">
                  <button
                    className="matrix-col-btn"
                    onClick={() => handleColClick(col)}
                    title={`Filter by ${colDef.label}: ${col}`}
                  >
                    {col}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row}>
                <td className="matrix-row">
                  <button
                    className="matrix-row-btn mono"
                    onClick={() => handleRowClick(row)}
                    title={`Filter by base: ${row}`}
                  >
                    {row}
                  </button>
                </td>
                {cols.map((col) => {
                  const names = cells.get(`${row}\x00${col}`);
                  const count = names?.length || 0;
                  return (
                    <td key={col} className="matrix-td">
                      <button
                        className={`matrix-cell ${count > 0 ? 'filled' : 'empty'}`}
                        disabled={count === 0}
                        onClick={count > 0 ? (e) => handleCellClick(row, col, e) : undefined}
                        title={count > 0 ? `${count} name${count !== 1 ? 's' : ''}` : undefined}
                      >
                        {count > 0 && (
                          <span className="matrix-cell-count">{count}</span>
                        )}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        {popover && (
          <div
            ref={popoverRef}
            className="matrix-popover"
            style={{ top: popover.rect.top, left: popover.rect.right + 8 }}
          >
            <div className="matrix-popover-head">
              <span className="matrix-popover-label mono">
                {popover.row} × {popover.col}
              </span>
              <button
                className="matrix-popover-close"
                onClick={() => setPopover(null)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>
            <ul className="matrix-popover-list">
              {popover.names.map((n) => (
                <li key={n.name}>
                  <button
                    className="matrix-popover-item mono"
                    onClick={() => { onSelect(n.name); setPopover(null); }}
                  >
                    {n.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="matrix-stats">
        <span className="mono">
          {totalWithCol} named entries · {rows.length}×{cols.length} shown
        </span>
      </div>
    </div>
  );
}
