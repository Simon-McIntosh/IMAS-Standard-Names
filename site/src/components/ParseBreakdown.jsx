import { useMemo } from 'react';
import { ROLE_META } from '../lib/grammar.js';

// Grammar token chips + highlighted source string + production footer.
//
// Consumes the pre-parsed `parse[]` array straight from the emitter —
// there is NO `parseSN` heuristic here. Spans in the original name are
// reconstructed by walking each token with a cursor.
//
// Each filterable token acts as a filter toggle via setFilters.
// (Named ParseBreakdown rather than GrammarTree because it's a flat
// token list with a source overlay, not a tree.)

const FILTERABLE_ROLES = new Set([
  'base', 'operator', 'reduction', 'modifier',
  'axis', 'locus', 'subject',
]);

export function ParseBreakdown({ name, parse, filters, setFilters }) {
  const spans = useMemo(() => {
    if (!parse || parse.length === 0) return [];
    const out = [];
    let cursor = 0;
    for (const t of parse) {
      const start = name.indexOf(t.text, cursor);
      if (start === -1) {
        // Token doesn't appear at or after the cursor — fall back to a
        // span at the current cursor. The visualisation still renders
        // (possibly mis-coloured) instead of blowing up.
        out.push({ ...t, start: cursor, end: cursor + t.text.length });
        cursor += t.text.length;
      } else {
        out.push({ ...t, start, end: start + t.text.length });
        cursor = start + t.text.length;
      }
    }
    return out;
  }, [name, parse]);

  if (!parse || parse.length === 0) {
    return (
      <div className="grammar">
        <div className="grammar-source mono">{name}</div>
      </div>
    );
  }

  const sourceSegments = (() => {
    const segs = [];
    let cursor = 0;
    spans.forEach((s, i) => {
      if (s.start > cursor) {
        segs.push(
          <span key={`u${i}`} className="grammar-sep">
            {name.slice(cursor, s.start)}
          </span>,
        );
      }
      segs.push(
        <span
          key={i}
          className={`grammar-span grammar-${s.role}`}
          style={{ '--role-hue': ROLE_META[s.role]?.hue ?? 0 }}
        >
          {s.text}
        </span>,
      );
      cursor = s.end;
    });
    if (cursor < name.length) {
      segs.push(
        <span key="rest" className="grammar-sep">
          {name.slice(cursor)}
        </span>,
      );
    }
    return segs;
  })();

  const isActiveFilter = (role, text) => filters?.[role]?.has(text) === true;
  const toggleFilter = (role, text) => {
    if (!setFilters) return;
    setFilters(f => {
      const cur = new Set(f[role] || []);
      cur.has(text) ? cur.delete(text) : cur.add(text);
      return { ...f, [role]: cur };
    });
  };

  return (
    <div className="grammar">
      <div className="grammar-source">{sourceSegments}</div>

      <div className="grammar-tree">
        {parse.map((t, i) => {
          const meta = ROLE_META[t.role] || ROLE_META.unknown;
          const filterable = FILTERABLE_ROLES.has(t.role);
          const active = isActiveFilter(t.role, t.text);
          return (
            <div
              key={i}
              className={`gtoken gtoken-${t.role} ${filterable ? 'clickable' : ''} ${active ? 'is-filter-active' : ''}`}
              style={{ '--role-hue': meta.hue }}
              onClick={() => filterable && toggleFilter(t.role, t.text)}
              title={
                filterable
                  ? (active ? `Remove ${t.role} filter` : `Filter to names with ${t.role} = ${t.text}`)
                  : meta.desc
              }
            >
              <div className="gtoken-role">
                {meta.label}
                {filterable && <span className="gtoken-filter-glyph" aria-hidden>{active ? '×' : '+'}</span>}
              </div>
              <div className="gtoken-text mono">{t.text}</div>
              <div className="gtoken-note">{meta.desc}</div>
            </div>
          );
        })}
      </div>

      <div className="grammar-foot">
        <span className="grammar-foot-label">Production:</span>
        <code className="grammar-prod">
          {parse.map((t) => `<${t.role}>`).join(' · ')}
        </code>
      </div>
    </div>
  );
}
