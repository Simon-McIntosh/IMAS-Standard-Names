import { useMemo, useState } from 'react';
import { ROLE_META, FILTERABLE_PARSE_ROLES } from '../lib/grammar.js';
import { useData } from '../lib/data.js';
import { StandardTermCard } from './StandardTermCard.jsx';

// Grammar token chips + highlighted source string + production footer.
//
// Consumes the pre-parsed `parse[]` array straight from the emitter —
// there is NO `parseSN` heuristic here. Spans in the original name are
// reconstructed by walking each token with a cursor.
//
// Each filterable token acts as a filter toggle via setFilters.
// (Named ParseBreakdown rather than GrammarTree because it's a flat
// token list with a source overlay, not a tree.)

// Single source of truth in grammar.js — a chip is filterable iff its role
// is an emitted, filterable parse role.
const FILTERABLE_ROLES = new Set(FILTERABLE_PARSE_ROLES);

// Strip the grammar connector from a locus/mechanism token so the chip shows
// the TRUE in-vocabulary token (``wall``, ``recombination``) and the connector
// (``at_``, ``due_to_``) falls into the grey separator gap — matching the
// Grammar tab. ``filterText`` keeps the emitter's original text so the facet
// filter still matches ``n.parse`` (which carries the connector-bearing form).
function displayToken(t) {
  if (t.role === 'locus') {
    const m = t.text.match(/^(of|at|over)_(.+)$/);
    if (m) return m[2];
  } else if (t.role === 'process' || t.role === 'mechanism') {
    const m = t.text.match(/^due_to_(.+)$/);
    if (m) return m[1];
  }
  return t.text;
}

export function ParseBreakdown({ name, parse, filters, setFilters }) {
  const { STANDARD_TERMS, NAMES } = useData();
  const [openTerm, setOpenTerm] = useState(null);
  const terms = useMemo(() => new Map((STANDARD_TERMS || []).map((term) => [term.token, term])), [STANDARD_TERMS]);
  const spans = useMemo(() => {
    if (!parse || parse.length === 0) return [];
    const out = [];
    let cursor = 0;
    for (const raw of parse) {
      const t = { ...raw, text: displayToken(raw), filterText: raw.text };
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
          // Filter on the emitter's original text; display the bare token.
          const active = isActiveFilter(t.role, t.text);
          const shown = displayToken(t);
          const term = terms.get(shown);
          return (
            <div
              key={i}
              className={`gtoken gtoken-${t.role} ${filterable ? 'clickable' : ''} ${active ? 'is-filter-active' : ''}`}
              style={{ '--role-hue': meta.hue }}
              onClick={() => term ? setOpenTerm(openTerm === term.token ? null : term.token) : filterable && toggleFilter(t.role, t.text)}
              title={
                term
                  ? term.definition
                  : filterable
                  ? (active ? `Remove ${t.role} filter` : `Filter to names with ${t.role} = ${shown}`)
                  : meta.desc
              }
            >
              <div className="gtoken-role">
                {meta.label}
                {filterable && <span className="gtoken-filter-glyph" aria-hidden>{active ? '×' : '+'}</span>}
              </div>
              <div className="gtoken-text mono">{shown}</div>
              <div className="gtoken-note">{meta.desc}</div>
            </div>
          );
        })}
      </div>

      {openTerm && (
        <StandardTermCard
          term={terms.get(openTerm)}
          examples={(NAMES || []).filter((entry) => entry.parse?.some((part) => displayToken(part) === openTerm)).map((entry) => entry.name)}
          onClose={() => setOpenTerm(null)}
        />
      )}

      <div className="grammar-foot">
        <span className="grammar-foot-label">Production:</span>
        <code className="grammar-prod">
          {parse.map((t) => `<${t.role}>`).join(' · ')}
        </code>
      </div>
    </div>
  );
}
