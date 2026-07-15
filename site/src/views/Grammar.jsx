import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../lib/data.js';
import { StandardTermCard } from '../components/StandardTermCard.jsx';
import {
  composeName,
  emptyState,
  matchesComposition,
  qualifierKind,
  seedFromParse,
} from '../lib/grammar-compose.js';

// Grammar view — a STRICT, grammar-faithful Standard-Name composer.
//
// Interaction model:
//   • the upper RAIL is select/deselect only — clicking a node toggles that
//     grammar segment into or out of the composition (no vocabulary dropdown);
//   • the composed-name CHIPS carry the dropdowns — click a chip to pick or
//     change its token.
// It mirrors the ISN grammar exactly (lib/grammar-compose.js, a JS mirror of
// imas_standard_names/grammar/render.py): operator · projection axis · an
// ORDERED qualifier list · required base · locus (with relation) · mechanism.
// Seeding reads a name's authoritative emitted parse[] (no in-browser parser,
// no vocabulary guessing) and the composition reconstructs the name verbatim.

const HUE = {
  operator: 320,
  projection: 200,
  base_physical: 260,
  base_geometric: 285,
  locus: 145,
  process: 290,
  aggregation: 65,
  orbit: 5,
  population: 25,
  subject: 15,
  zone: 95,
  channel_qualifier: 135,
  channel: 175,
  qualifier: 35,
};

const REL_BY_TYPE = { entity: ['of'], position: ['at', 'of'], geometry: ['of'], region: ['over'] };

// Named qualifier sub-kinds get their own rail toggle; the generic 'qualifier'
// node covers everything else. `key` = GRAMMAR_VOCAB section, `kind` =
// qualifierKind label.
// Order is the canonical segment order so the picker surfaces these groups
// (and the relabelled top-row buttons read) aggregation → orbit → population →
// subject → zone → channel, matching the ISN render order. zone is an ordered
// MULTI-token segment (a name may carry several, e.g. lower_outer); channel is
// SINGLE-token. Both peel through ir.qualifiers, so they live in the same
// ordered qualifier list as the others — parse order IS canonical order.
const QUAL_GROUPS = [
  { key: 'aggregations', kind: 'aggregation', label: 'aggregation' },
  { key: 'orbits', kind: 'orbit', label: 'orbit' },
  { key: 'populations', kind: 'population', label: 'population' },
  { key: 'subjects', kind: 'subject', label: 'subject' },
  { key: 'zones', kind: 'zone', label: 'zone' },
  { key: 'channel_qualifiers', kind: 'channel_qualifier', label: 'channel qualifier' },
  { key: 'channels', kind: 'channel', label: 'channel' },
];

// The display GROUP for a qualifier token: a named sub-kind
// (aggregation/orbit/population/subject) if it is one, otherwise the generic
// qualifier's emitted category (transport/state/geometry/…). Drives the
// top-row button label so a generic reads e.g. "state −", not "qualifier −".
function qualifierGroup(token, vocab) {
  if (!token) return null;
  const k = qualifierKind(token, vocab);
  if (k !== 'qualifier') return k;
  const entry = (vocab.qualifiers || []).find((t) => t.token === token);
  return entry?.category || 'qualifier';
}

function locusRelationsFor(vocab, token) {
  const reg = (vocab.locus_registry || []).find((x) => x.token === token);
  if (reg) return reg.relations?.length ? reg.relations : REL_BY_TYPE[reg.type] || ['of'];
  if ((vocab.regions || []).some((r) => r.token === token)) return ['over'];
  return ['of'];
}

function JumpArrow() {
  return (
    <svg className="jump-arrow" width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M5 11L11 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M6 5h5v5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---- vocabulary dropdown -------------------------------------------------
// Single-select (chips) by default. In `multi` mode (the qualifier picker)
// rows are toggles showing a ✓ when selected, the picker stays open as you
// pick several, and the single-select "× remove" affordance is hidden.
function VocabDropdown({ title, hue, options, grouped, anchor, count, current, multi, selected, onChoose, onClear, onClose }) {
  const [term, setTerm] = useState('');
  const ref = useRef(null);
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    window.addEventListener('keydown', onKey);
    const id = setTimeout(() => document.addEventListener('mousedown', onDown), 0);
    return () => {
      window.removeEventListener('keydown', onKey);
      clearTimeout(id);
      document.removeEventListener('mousedown', onDown);
    };
  }, [onClose]);

  const q = term.trim().toLowerCase();
  const matches = (t) => !q || t.token.includes(q) || (t.note && t.note.toLowerCase().includes(q)) || (t.definition && t.definition.toLowerCase().includes(q)) || (t.abbreviations || []).some((a) => a.toLowerCase().includes(q));
  const score = (items) =>
    items
      .filter(matches)
      .map((t) => ({ t, c: count(t.token) }))
      .sort((a, b) => b.c - a.c || a.t.token.localeCompare(b.t.token));

  const total = grouped ? options.reduce((a, g) => a + g.items.length, 0) : options.length;
  const groups = grouped ? options.map((g) => ({ label: g.label, rows: score(g.items) })) : null;
  const flat = grouped ? null : score(options);

  const W = 300;
  const H = 380;
  const left = Math.max(8, Math.min(anchor.x, window.innerWidth - W - 8));
  const top = Math.min(anchor.y + 6, window.innerHeight - H - 8);

  const isSel = (tok) => (multi ? selected?.has(tok) : current === tok);
  const Row = ({ t, c }) => (
    <button
      className={`gx-dd-row ${c > 0 ? 'is-avail' : 'is-dead'} ${isSel(t.token) ? 'is-current' : ''}`}
      onClick={() => onChoose(t.token)}
      title={t.note || t.token}
    >
      {multi && <span className="gx-dd-check" aria-hidden>{isSel(t.token) ? '✓' : ''}</span>}
      <span className="gx-dd-tok mono">{t.token}</span>
      <span className="gx-dd-count">{c || '—'}</span>
    </button>
  );

  return (
    <div className="gx-dd" ref={ref} style={{ left, top, '--role-hue': hue }}>
      <div className="gx-dd-head">
        <span className="gx-dd-title">{title}</span>
        <span className="gx-dd-sub">
          {total} in vocabulary · <b>bold</b> = in catalog{multi ? ' · pick any' : ''}
        </span>
      </div>
      <input className="gx-dd-search mono" autoFocus value={term}
        onChange={(e) => setTerm(e.target.value)} placeholder="filter vocabulary…" spellCheck="false" />
      <div className="gx-dd-list">
        {!multi && current && <button className="gx-dd-clear" onClick={onClear}>× remove</button>}
        {groups &&
          groups.map((g) => (
            <div key={g.label} className="gx-dd-group">
              <div className="gx-dd-grouph">{g.label}<span className="gx-dd-groupn">{g.rows.length}</span></div>
              {g.rows.map(({ t, c }) => <Row key={t.token} t={t} c={c} />)}
              {g.rows.length === 0 && <div className="gx-dd-empty">—</div>}
            </div>
          ))}
        {flat && flat.map(({ t, c }) => <Row key={t.token} t={t} c={c} />)}
        {flat && flat.length === 0 && <div className="gx-dd-empty">no tokens match “{term}”</div>}
      </div>
    </div>
  );
}

// ---- rail node: pure toggle (no dropdown) --------------------------------
function RailNode({ label, hue, on, filled, onToggle, title, caret }) {
  return (
    <button
      className={`gx-node is-opt ${on ? 'is-on' : 'is-off'} ${filled ? 'is-filled' : ''}`}
      style={{ '--role-hue': hue }}
      onClick={onToggle}
      title={title}
    >
      <span className="gx-node-dot" aria-hidden />
      <span className="gx-node-label">{label}</span>
      <span className="gx-node-tick" aria-hidden>{caret ? '▾' : on ? '−' : '+'}</span>
    </button>
  );
}

// ---- main ----------------------------------------------------------------
export function Grammar({ onSelect, setView, query, seedName, seedNonce, term = '', setTerm }) {
  const { NAMES, GRAMMAR_VOCAB, STANDARD_TERMS } = useData();
  const V = GRAMMAR_VOCAB || {};

  const [state, setState] = useState(emptyState);
  const [open, setOpen] = useState(null); // { target }
  const nameRef = useRef(null); // STANDARD NAME row — dropdowns anchor below it
  const update = (fn) => setState((s) => fn(structuredClone(s)));

  const nameStates = useMemo(() => {
    const m = new Map();
    for (const n of NAMES) m.set(n.name, seedFromParse(n.parse, V, n.name));
    return m;
  }, [NAMES, V]);

  const loadName = (nm) => {
    if (!nm) return;
    const ns = nameStates.get(nm);
    setState(ns ? structuredClone(ns) : emptyState());
    setOpen(null);
  };
  useEffect(() => {
    if (seedName && nameStates.size) loadName(seedName);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedNonce, nameStates]);

  // Generic qualifiers, grouped by the normalized category emitted in
  // GRAMMAR_VOCAB (authoritative — categorized in ISN by qualifier_categories.yml,
  // no SPA-side subtraction or named sub-kinds mixed in). The picker for a
  // generic 'qualifier' chip sub-groups by these categories.
  const QUALIFIER_CATEGORY_ORDER = [
    'transport', 'source', 'geometry', 'region', 'state', 'energy',
    'diagnostic', 'polarization', 'temporal', 'normalized', 'species', 'engineering',
  ];
  const categoryGroups = useMemo(() => {
    const byCat = new Map();
    for (const t of V.qualifiers || []) {
      const c = t.category || 'other';
      if (!byCat.has(c)) byCat.set(c, []);
      byCat.get(c).push(t);
    }
    const known = QUALIFIER_CATEGORY_ORDER.filter((c) => byCat.has(c));
    const extra = [...byCat.keys()].filter((c) => !QUALIFIER_CATEGORY_ORDER.includes(c)).sort();
    return [...known, ...extra].map((c) => ({ label: c, items: byCat.get(c) }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [V]);

  // The single qualifier picker: the named sub-kinds first (in canonical
  // aggregation→orbit→population→subject order), then the generic qualifiers
  // grouped by category. All are qualifiers in the IR; the named ones are just
  // surfaced as their own groups.
  const qualifierPickerGroups = useMemo(
    () => [
      ...QUAL_GROUPS.map((g) => ({ label: g.label, items: V[g.key] || [] })),
      ...categoryGroups,
    ].filter((g) => g.items.length),
    [V, categoryGroups],
  );
  const composed = composeName(state);
  const exists = composed && nameStates.has(composed);

  const q = (query || '').trim().toLowerCase();
  const [selectedTerm, setSelectedTerm] = useState(term);
  useEffect(() => setSelectedTerm(term), [term]);
  const chooseTerm = (token) => { setSelectedTerm(token); setTerm?.(token); };
  const visibleTerms = useMemo(() => {
    const needle = q;
    return (STANDARD_TERMS || []).filter((term) => {
      const haystack = [term.token, term.definition, ...(term.abbreviations || [])].join(' ').toLowerCase();
      return !needle || needle.split(/\s+/).every((word) => haystack.includes(word));
    });
  }, [STANDARD_TERMS, q]);
  const results = useMemo(
    () =>
      NAMES.filter(
        (n) =>
          matchesComposition(nameStates.get(n.name), state) &&
          (!q || n.name.includes(q) || (n.short && n.short.toLowerCase().includes(q))),
      ),
    [NAMES, nameStates, state, q],
  );

  const hasConstraints =
    !!(state.operator || state.axis || state.base || state.locus || state.mechanism) ||
    state.qualifiers.length > 0;

  // ---- rail segment buttons ----------------------------------------------
  // Every segment is added from its top-row button and its token is picked in
  // the dropdown that opens BELOW the STANDARD NAME row — symmetric for all
  // segments, including the (repeatable) qualifier. A top button that is
  // already present removes its segment; the lower-row chip re-opens the
  // picker to change the token.
  const openSeg = (target) => setOpen({ target });
  const toggleOperator = () =>
    state.operator
      ? (update((s) => { s.operator = null; return s; }), setOpen(null))
      : (update((s) => { s.operator = { token: null, kind: null }; return s; }), openSeg({ seg: 'operator' }));
  const toggleProjection = (baseKind) => {
    if (state.axis) { update((s) => { s.axis = null; return s; }); setOpen(null); }
    else {
      update((s) => { s.axis = { token: null }; if (s.base) s.base.kind = baseKind; return s; });
      openSeg({ seg: 'projection' });
    }
  };
  const toggleBase = (baseKind) => {
    if (state.base && state.base.kind === baseKind) { update((s) => { s.base = null; return s; }); setOpen(null); }
    else { update((s) => { s.base = { token: s.base?.token ?? null, kind: baseKind }; return s; }); openSeg({ seg: 'base' }); }
  };
  const toggleLocus = () =>
    state.locus
      ? (update((s) => { s.locus = null; return s; }), setOpen(null))
      : (update((s) => { s.locus = { token: null, relation: 'of' }; return s; }), openSeg({ seg: 'locus' }));
  const toggleProcess = () =>
    state.mechanism
      ? (update((s) => { s.mechanism = null; return s; }), setOpen(null))
      : (update((s) => { s.mechanism = { token: null }; return s; }), openSeg({ seg: 'process' }));

  // Qualifier is repeatable: "qualifier +" appends a placeholder instance and
  // opens its picker; picking a token sets the instance's group (kind), which
  // relabels its top-row button (e.g. "orbit −"). Order is currently insertion/
  // parse order — canonical ordering of the qualifier buttons is wired by the
  // canonical-qualifier-order plan. Clicking a qualifier's top button removes it.
  const addQualifier = () => {
    const index = state.qualifiers.length;
    update((s) => { s.qualifiers.push({ token: null, kind: null }); return s; });
    openSeg({ seg: 'qualifier', index });
  };
  const removeQualifier = (index) => {
    update((s) => { s.qualifiers.splice(index, 1); return s; });
    setOpen(null);
  };

  // ---- composed-name chip dropdowns --------------------------------------
  // Re-open the picker for an already-present segment (from its lower chip).
  const openDD = (target) =>
    setOpen((o) =>
      o && o.target.seg === target.seg && o.target.index === target.index ? null : { target },
    );

  const choose = (token) => {
    const t = open.target;
    update((s) => {
      switch (t.seg) {
        case 'operator': {
          const o = (V.operators || []).find((x) => x.token === token);
          s.operator = { token, kind: o ? o.kind : 'unary_prefix' };
          break;
        }
        case 'projection': s.axis = { token }; break;
        case 'base': {
          const physical = (V.physical_bases || []).some((b) => b.token === token);
          s.base = { token, kind: physical ? 'physical' : 'geometric' };
          break;
        }
        case 'locus': s.locus = { token, relation: locusRelationsFor(V, token)[0] }; break;
        case 'process': s.mechanism = { token }; break;
        case 'qualifier': s.qualifiers[t.index] = { token, kind: qualifierGroup(token, V) }; break;
        default: break;
      }
      return s;
    });
    setOpen(null);
  };

  const clearSlot = () => {
    const t = open.target;
    update((s) => {
      switch (t.seg) {
        case 'operator': s.operator = null; break;
        case 'projection': s.axis = null; break;
        case 'base': s.base = null; break;
        case 'locus': s.locus = null; break;
        case 'process': s.mechanism = null; break;
        case 'qualifier': s.qualifiers.splice(t.index, 1); break;
        default: break;
      }
      return s;
    });
    setOpen(null);
  };

  const cycleLocusRel = () =>
    update((s) => {
      if (!s.locus?.token) return s;
      const al = locusRelationsFor(V, s.locus.token);
      if (al.length > 1) s.locus.relation = al[(al.indexOf(s.locus.relation) + 1) % al.length];
      return s;
    });

  const clearAll = () => { setState(emptyState()); setOpen(null); };

  // residual corpus for dropdown counts (all constraints except the open slot)
  const residual = useMemo(() => {
    if (!open) return NAMES;
    const probe = structuredClone(state);
    switch (open.target.seg) {
      case 'operator': probe.operator = null; break;
      case 'projection': probe.axis = null; break;
      case 'base': probe.base = null; break;
      case 'locus': probe.locus = null; break;
      case 'process': probe.mechanism = null; break;
      case 'qualifier': probe.qualifiers.splice(open.target.index, 1); break;
      default: break;
    }
    return NAMES.filter((n) => matchesComposition(nameStates.get(n.name), probe));
  }, [open, NAMES, nameStates, state]);

  const counter = (target) => (token) => {
    const key = {
      operator: (ns) => ns.operator?.token === token,
      projection: (ns) => ns.axis?.token === token,
      base: (ns) => ns.base?.token === token,
      locus: (ns) => ns.locus?.token === token,
      process: (ns) => ns.mechanism?.token === token,
      qualifier: (ns) => (ns.qualifiers || []).some((x) => x.token === token),
    }[target.seg];
    return residual.filter((n) => key(nameStates.get(n.name) || {})).length;
  };

  // ---- dropdown config for the open chip ---------------------------------
  // The dropdown opens BELOW the STANDARD NAME row (anchored to the namebar),
  // the same way for every segment — including each qualifier instance, whose
  // picker is grouped by sub-kind + category.
  const dropdown = () => {
    if (!open) return null;
    const t = open.target;
    const rect = nameRef.current?.getBoundingClientRect();
    const anchor = rect ? { x: rect.left, y: rect.bottom } : { x: 40, y: 220 };
    const cfg = {
      operator: { title: 'operator', hue: HUE.operator, options: V.operators || [], current: state.operator?.token },
      projection: {
        title: state.base?.kind === 'geometric' ? 'coordinate' : 'component',
        hue: HUE.projection, options: V.components || [], current: state.axis?.token,
      },
      base: {
        title: state.base?.kind === 'geometric' ? 'geometric base' : 'physical base',
        hue: state.base?.kind === 'geometric' ? HUE.base_geometric : HUE.base_physical,
        options: state.base?.kind === 'geometric' ? V.geometry_carriers || [] : V.physical_bases || [],
        current: state.base?.token,
      },
      locus: {
        title: 'locus', hue: HUE.locus,
        options: [...(V.locus_registry || []), ...(V.regions || [])], current: state.locus?.token,
      },
      process: { title: 'process', hue: HUE.process, options: V.processes || [], current: state.mechanism?.token },
      qualifier: {
        title: 'qualifier', hue: HUE.qualifier, grouped: true, options: qualifierPickerGroups,
        current: state.qualifiers[t.index]?.token,
      },
    }[t.seg];
    return (
      <VocabDropdown
        title={cfg.title} hue={cfg.hue} options={cfg.options} grouped={cfg.grouped}
        anchor={anchor} count={counter(t)} current={cfg.current}
        onChoose={choose} onClear={clearSlot} onClose={() => setOpen(null)}
      />
    );
  };

  // ---- composition bar ----------------------------------------------------
  const isPostfix = state.operator?.kind === 'unary_postfix';
  const isOpen = (seg, index) => open && open.target.seg === seg && open.target.index === index;

  const chip = (key, label, token, hue, target) => (
    <button
      key={key}
      className={`gx-tok ${token ? 'is-filled' : 'is-empty'} ${isOpen(target.seg, target.index) ? 'is-open' : ''}`}
      style={{ '--role-hue': hue }}
      onClick={() => openDD(target)}
      title={token ? `${label} = ${token} — click to change` : `choose a ${label}`}
    >
      {token ? <span className="mono">{token}</span> : <span className="gx-tok-ph">{label}</span>}
      <svg className="gx-tok-caret" width="9" height="9" viewBox="0 0 12 12">
        <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
  // Top-row button for a qualifier instance: labelled by its group (or the
  // placeholder "qualifier" until a token is picked), with a "−" to remove —
  // symmetric with the other segment buttons. Click removes the instance.
  const qbtn = (kind, index) => (
    <RailNode
      key={`qb${index}`}
      label={kind || 'qualifier'}
      hue={HUE[kind] ?? HUE.qualifier}
      on
      filled={!!state.qualifiers[index]?.token}
      onToggle={() => removeQualifier(index)}
      title={kind ? `${kind} qualifier — click to remove` : 'qualifier (pick a token below) — click to remove'}
    />
  );
  const sep = (key, text) => <span key={key} className="gx-sep mono">{text}</span>;

  const bar = [];
  let needSep = false;
  const maybeSep = (k) => { if (needSep) bar.push(sep(k, '_')); };

  if (state.operator && !isPostfix) {
    bar.push(chip('op', 'operator', state.operator.token, HUE.operator, { seg: 'operator' }));
    bar.push(sep('ops', '_of_'));
    needSep = false;
  }
  if (state.axis) {
    maybeSep('axs');
    bar.push(chip('axis', state.base?.kind === 'geometric' ? 'coordinate' : 'component', state.axis.token, HUE.projection, { seg: 'projection' }));
    needSep = true;
  }
  state.qualifiers.forEach((qq, i) => {
    maybeSep('qs' + i);
    const k = qualifierGroup(qq.token, V) || 'qualifier';
    bar.push(chip('q' + i, k, qq.token, HUE[k] ?? HUE.qualifier, { seg: 'qualifier', index: i }));
    needSep = true;
  });
  maybeSep('bs');
  bar.push(chip('base', 'base', state.base?.token, state.base?.kind === 'geometric' ? HUE.base_geometric : HUE.base_physical, { seg: 'base' }));
  needSep = true;
  if (state.locus) {
    const allowed = state.locus.token ? locusRelationsFor(V, state.locus.token) : ['of', 'at', 'over'];
    if (allowed.length > 1) {
      bar.push(
        <button key="rel" className="gx-relsw mono" onClick={cycleLocusRel}
          title={`locus relation — ${allowed.join(' | ')} valid here; click to switch`}>
          _{state.locus.relation}_<span className="gx-relsw-cue" aria-hidden>⇅</span>
        </button>,
      );
    } else {
      bar.push(sep('rels', `_${state.locus.relation}_`));
    }
    bar.push(chip('locus', 'locus', state.locus.token, HUE.locus, { seg: 'locus' }));
    needSep = true;
  }
  if (state.mechanism) {
    bar.push(sep('mechs', '_due_to_'));
    bar.push(chip('mech', 'process', state.mechanism.token, HUE.process, { seg: 'process' }));
    needSep = true;
  }
  if (state.operator && isPostfix) {
    bar.push(sep('ops2', '_'));
    bar.push(chip('op', 'operator', state.operator.token, HUE.operator, { seg: 'operator' }));
  }

  // production line
  const prod = [];
  const pConn = (k, txt) => prod.push(<span key={k} className="gx-prod-conn mono">{txt}</span>);
  const pSeg = (k, label, hue) => prod.push(<span key={k} className="gx-prod-seg" style={{ '--role-hue': hue }}>&lt;{label}&gt;</span>);
  if (state.operator && !isPostfix) { pSeg('po', 'operator', HUE.operator); pConn('poc', 'of_'); }
  if (state.axis) pSeg('pa', state.base?.kind === 'geometric' ? 'coordinate' : 'component', HUE.projection);
  state.qualifiers.forEach((qq, i) => {
    const k = qualifierGroup(qq.token, V) || 'qualifier';
    pSeg('pq' + i, k, HUE[k] ?? HUE.qualifier);
  });
  pSeg('pb', state.base?.kind === 'geometric' ? 'geometric base' : 'base', state.base?.kind === 'geometric' ? HUE.base_geometric : HUE.base_physical);
  if (state.locus) { pConn('plc', `${state.locus.relation}_`); pSeg('pl', 'locus', HUE.locus); }
  if (state.mechanism) { pConn('pmc', 'due_to_'); pSeg('pm', 'process', HUE.process); }
  if (state.operator && isPostfix) pSeg('po2', 'operator', HUE.operator);

  const anySegment = state.base || state.qualifiers.length || state.axis || state.operator || state.locus || state.mechanism;

  return (
    <div className="grammar-view" data-active-view="grammar">
      <div className="gx-chain">
        <div className="gx-chain-head"><span className="gx-chain-k">grammar</span></div>
        <div className="gx-rail">
          <RailNode label="operator" hue={HUE.operator} on={!!state.operator} filled={!!state.operator?.token}
            onToggle={toggleOperator} title="Operator (prefix / postfix)" />
          <span className="gx-rail-link" />
          <RailNode label="component" hue={HUE.projection}
            on={!!state.axis && state.base?.kind !== 'geometric'} filled={!!state.axis?.token}
            onToggle={() => toggleProjection('physical')} title="Vector component (projection of a physical base)" />
          <span className="gx-alt-pipe" aria-hidden>|</span>
          <RailNode label="coordinate" hue={HUE.projection}
            on={!!state.axis && state.base?.kind === 'geometric'} filled={!!state.axis?.token}
            onToggle={() => toggleProjection('geometric')} title="Coordinate (projection of a geometric base)" />
          <span className="gx-rail-link" />
          {state.qualifiers.map((qq, i) => qbtn(qualifierGroup(qq.token, V), i))}
          <RailNode label="qualifier" hue={HUE.qualifier} caret on={false} filled={false}
            onToggle={addQualifier}
            title="Add a qualifier — opens the grouped picker below; the button relabels to its group (e.g. orbit) once chosen" />
          <span className="gx-rail-link" />
          <RailNode label="physical base" hue={HUE.base_physical}
            on={state.base?.kind === 'physical'} filled={state.base?.kind === 'physical' && !!state.base?.token}
            onToggle={() => toggleBase('physical')} title="Physical base quantity" />
          <span className="gx-alt-pipe" aria-hidden>|</span>
          <RailNode label="geometric base" hue={HUE.base_geometric}
            on={state.base?.kind === 'geometric'} filled={state.base?.kind === 'geometric' && !!state.base?.token}
            onToggle={() => toggleBase('geometric')} title="Geometric carrier base" />
          <span className="gx-conn mono">of_/at_/over_</span>
          <RailNode label="locus" hue={HUE.locus} on={!!state.locus} filled={!!state.locus?.token}
            onToggle={toggleLocus} title="Locus (object / position / region)" />
          <span className="gx-conn mono">due_to_</span>
          <RailNode label="process" hue={HUE.process} on={!!state.mechanism} filled={!!state.mechanism?.token}
            onToggle={toggleProcess} title="Mechanism (due_to)" />
        </div>
      </div>

      <div className="gx-comp">
        <div className="gx-comp-head">
          {composed && exists ? (
            <button className="gx-comp-k is-link" onClick={() => { onSelect(composed); setView('browse'); }}
              title={`Open ${composed} in Browse`}>
              standard name<JumpArrow />
            </button>
          ) : (
            <span className="gx-comp-k">standard name</span>
          )}
          {hasConstraints && <button className="gx-clear" onClick={clearAll}>clear</button>}
        </div>
        <div className="gx-namebar" ref={nameRef}>
          {!anySegment ? <span className="gx-name-empty">add a grammar segment above to begin</span> : bar}
        </div>
        {anySegment ? (
          <div className="gx-prod">
            <span className="gx-prod-k">production</span>
            <code className="gx-prod-body">{prod}</code>
          </div>
        ) : null}
      </div>

      <div className="gx-results">
        <div className="gx-results-meta">
          <strong>{results.length}</strong> {results.length === 1 ? 'name' : 'names'}
          {hasConstraints ? ' match this composition' : ' in the catalog'}
          {q ? <> · filtered by “{query.trim()}”</> : null}
        </div>
        {results.length === 0 ? (
          <div className="gx-empty">
            No catalogued name matches this combination — the composition is grammatically valid but not yet in the catalog.
          </div>
        ) : (
          <ul className="gx-list">
            {results.slice(0, 500).map((n) => (
              <li key={n.name}>
                <button className={`gx-name mono ${n.name === composed ? 'is-hit' : ''}`}
                  onClick={() => loadName(n.name)} title={`Load ${n.name} into the builder`}>
                  {n.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <section className="standard-terms" aria-labelledby="standard-terms-heading">
        <div className="standard-terms-head">
          <h2 id="standard-terms-heading">Standard terms</h2>
          <span>{visibleTerms.length} governed compositional terms</span>
        </div>
        <div className="standard-terms-list">
          {visibleTerms.slice(0, 100).map((term) => (
            <button key={term.token} className="standard-term-row" onClick={() => chooseTerm(term.token)} title={term.definition}>
              <code>{term.token}</code><span>{term.segment}</span>
              {term.abbreviations?.length > 0 && <small>{term.abbreviations.join(', ')}</small>}
            </button>
          ))}
        </div>
        {selectedTerm && <StandardTermCard term={(STANDARD_TERMS || []).find((term) => term.token === selectedTerm)}
          examples={NAMES.filter((entry) => entry.parse?.some((part) => part.text.endsWith(selectedTerm))).map((entry) => entry.name)}
          onClose={() => { setSelectedTerm(''); setTerm?.(''); }} />}
      </section>

      {dropdown()}
    </div>
  );
}
