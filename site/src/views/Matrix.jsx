import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../lib/data.js';

const ROW_CAP = 20;
const COL_CAP = 14;

const MATRIX_COLS = [
  {
    id: 'axis', label: 'Axis', roleHue: 200,
    get: (n) => n.parse?.find((t) => t.role === 'axis')?.text || null,
  },
  {
    id: 'locus', label: 'Locus', roleHue: 145,
    get: (n) => n.parse?.find((t) => t.role === 'locus')?.text || null,
  },
  {
    id: 'operator', label: 'Operator', roleHue: 320,
    get: (n) => n.parse?.find((t) => t.role === 'operator')?.text || null,
  },
  {
    id: 'reduction', label: 'Reduction', roleHue: 65,
    get: (n) => n.parse?.find((t) => t.role === 'reduction')?.text || null,
  },
  {
    id: 'subject', label: 'Subject', roleHue: 15,
    get: (n) => n.parse?.find((t) => t.role === 'subject')?.text || n.subject || null,
  },
  {
    id: 'process', label: 'Mechanism', roleHue: 290,
    get: (n) => n.parse?.find((t) => t.role === 'process' || t.role === 'mechanism')?.text || null,
  },
  {
    id: 'category', label: 'Domain', roleHue: null,
    get: (n) => n.category || null,
  },
];

function prettyMatrixLabel(value) {
  if (!value) return '';
  return value.replace(/^(?:at|of|due_to)_/, '').replace(/_/g, ' ');
}

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
  const [colId, setColId] = useState(MATRIX_COLS[0].id);
  const [popover, setPopover] = useState(null);
  const popoverRef = useRef(null);

  const colDef = MATRIX_COLS.find((c) => c.id === colId) ?? MATRIX_COLS[0];

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
    setFilters((prev) => ({ ...prev, [colDef.id]: new Set([col]) }));
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
        <div className="seg matrix-col-seg" role="group" aria-label="Grammar segment">
          {MATRIX_COLS.map((c) => (
            <button
              key={c.id}
              className={colId === c.id ? 'on' : ''}
              style={c.roleHue != null ? { '--role-hue': c.roleHue } : undefined}
              onClick={() => { setColId(c.id); setPopover(null); }}
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
                <th key={col} className="matrix-col" title={col}>
                  <button
                    className="matrix-col-btn"
                    onClick={() => handleColClick(col)}
                  >
                    {prettyMatrixLabel(col)}
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
                  >
                    {prettyMatrixLabel(row)}
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

    </div>
  );
}
