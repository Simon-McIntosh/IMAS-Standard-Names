import { useMemo } from 'react';
import { useData } from '../lib/data.js';
import { ROLE_META, CLICKABLE_ROLES } from '../lib/grammar.js';

// Grammar token chips + highlighted source string + production footer.
//
// Consumes the pre-parsed `parse[]` array straight from the emitter —
// there is NO `parseSN` heuristic here. Spans in the original name are
// reconstructed by walking each token with a cursor.
//
// (Named ParseBreakdown rather than GrammarTree because it's a flat
// token list with a source overlay, not a tree.)
export function ParseBreakdown({ name, parse, onSelect }) {
  const { NAMES } = useData();
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

  return (
    <div className="grammar">
      <div className="grammar-source">{sourceSegments}</div>

      <div className="grammar-tree">
        {parse.map((t, i) => {
          const meta = ROLE_META[t.role] || ROLE_META.unknown;
          const isClickable =
            CLICKABLE_ROLES.has(t.role) && NAMES.some((n) => n.name === t.text);
          return (
            <div
              key={i}
              className={`gtoken gtoken-${t.role} ${isClickable ? 'clickable' : ''}`}
              style={{ '--role-hue': meta.hue }}
              onClick={() => isClickable && onSelect(t.text)}
              title={isClickable ? `Open ${t.text}` : meta.desc}
            >
              <div className="gtoken-role">{meta.label}</div>
              <div className="gtoken-text mono">{t.text}</div>
              <div className="gtoken-note">{t.note || meta.desc}</div>
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
