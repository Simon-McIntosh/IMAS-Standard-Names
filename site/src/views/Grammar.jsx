import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../lib/data.js';
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
  qualifier: 35,
};

const REL_BY_TYPE = { entity: ['of'], position: ['at', 'of'], geometry: ['of'], region: ['over'] };

// Named qualifier sub-kinds get their own rail toggle; the generic 'qualifier'
// node covers everything else. `key` = GRAMMAR_VOCAB section, `kind` =
// qualifierKind label.
const QUAL_GROUPS = [
  { key: 'aggregations', kind: 'aggregation', label: 'aggregation' },
  { key: 'orbits', kind: 'orbit', label: 'orbit' },
  { key: 'populations', kind: 'population', label: 'population' },
  { key: 'subjects', kind: 'subject', label: 'subject' },
];

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

// ---- vocabulary dropdown (composed-name chips only) ----------------------
function VocabDropdown({ title, hue, options, grouped, anchor, count, current, onChoose, onClear, onClose }) {
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
  const matches = (t) => !q || t.token.includes(q) || (t.note && t.note.toLowerCase().includes(q));
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

  const Row = ({ t, c }) => (
    <button
      className={`gx-dd-row ${c > 0 ? 'is-avail' : 'is-dead'} ${current === t.token ? 'is-current' : ''}`}
      onClick={() => onChoose(t.token)}
      title={t.note || t.token}
    >
      <span className="gx-dd-tok mono">{t.token}</span>
      <span className="gx-dd-count">{c || '—'}</span>
    </button>
  );

  return (
    <div className="gx-dd" ref={ref} style={{ left, top, '--role-hue': hue }}>
      <div className="gx-dd-head">
        <span className="gx-dd-title">{title}</span>
        <span className="gx-dd-sub">{total} in vocabulary · <b>bold</b> = in catalog</span>
      </div>
      <input className="gx-dd-search mono" autoFocus value={term}
        onChange={(e) => setTerm(e.target.value)} placeholder="filter vocabulary…" spellCheck="false" />
      <div className="gx-dd-list">
        {current && <button className="gx-dd-clear" onClick={onClear}>× remove</button>}
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
function RailNode({ label, hue, on, filled, onToggle, title }) {
  return (
    <button
      className={`gx-node is-opt ${on ? 'is-on' : 'is-off'} ${filled ? 'is-filled' : ''}`}
      style={{ '--role-hue': hue }}
      onClick={onToggle}
      title={title}
    >
      <span className="gx-node-dot" aria-hidden />
      <span className="gx-node-label">{label}</span>
      <span className="gx-node-tick" aria-hidden>{on ? '−' : '+'}</span>
    </button>
  );
}

// ---- main ----------------------------------------------------------------
export function Grammar({ onSelect, setView, query, seedName, seedNonce }) {
  const { NAMES, GRAMMAR_VOCAB } = useData();
  const V = GRAMMAR_VOCAB || {};

  const [state, setState] = useState(emptyState);
  const [open, setOpen] = useState(null); // { target, anchor }
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

  // Genuine generic qualifiers: the qualifier vocab minus the named sub-kinds
  // AND minus tokens that really belong to other segments (locus entities,
  // operators, components, bases) — the parser accepts those as qualifiers for
  // matching, but they are not qualifiers and must not be offered here.
  const otherQualifiers = useMemo(() => {
    const claimed = new Set();
    const add = (key) => (V[key] || []).forEach((t) => claimed.add(t.token));
    ['aggregations', 'orbits', 'populations', 'subjects', 'locus_registry', 'operators',
      'components', 'coordinate_axes', 'physical_bases', 'geometry_carriers'].forEach(add);
    return (V.qualifiers || []).filter((t) => !claimed.has(t.token));
  }, [V]);

  const composed = composeName(state);
  const exists = composed && nameStates.has(composed);

  const q = (query || '').trim().toLowerCase();
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

  const hasQual = (kind) => state.qualifiers.some((qq) => (qq.kind || qualifierKind(qq.token, V)) === kind);

  // ---- rail toggles (presence only) --------------------------------------
  const toggleOperator = () => update((s) => { s.operator = s.operator ? null : { token: null, kind: null }; return s; });
  const toggleProjection = (baseKind) =>
    update((s) => {
      if (s.axis) { s.axis = null; }
      else { s.axis = { token: null }; if (s.base) s.base.kind = baseKind; }
      return s;
    });
  const toggleBase = (baseKind) =>
    update((s) => {
      if (s.base && s.base.kind === baseKind) s.base = null;
      else {
        s.base = { token: s.base?.token ?? null, kind: baseKind };
        // couple the projection: physical↔component, geometric↔coordinate
        // (the projection token carries across; only its base-kind view flips)
      }
      return s;
    });
  const toggleLocus = () => update((s) => { s.locus = s.locus ? null : { token: null, relation: 'of' }; return s; });
  const toggleProcess = () => update((s) => { s.mechanism = s.mechanism ? null : { token: null }; return s; });
  const toggleQualKind = (kind) =>
    update((s) => {
      const i = s.qualifiers.findIndex((qq) => (qq.kind || qualifierKind(qq.token, V)) === kind);
      if (i >= 0) s.qualifiers.splice(i, 1);
      else s.qualifiers.push({ token: null, kind });
      return s;
    });
  const addGenericQualifier = () =>
    update((s) => { s.qualifiers.push({ token: null, kind: 'qualifier' }); return s; });

  // ---- composed-name chip dropdowns --------------------------------------
  const openDD = (target, el) => {
    const r = el.getBoundingClientRect();
    setOpen((o) =>
      o && o.target.seg === target.seg && o.target.index === target.index
        ? null
        : { target, anchor: { x: r.left, y: r.bottom } },
    );
  };

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
        case 'qualifier':
          s.qualifiers[t.index] = { token, kind: qualifierKind(token, V) };
          break;
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
  const dropdown = () => {
    if (!open) return null;
    const t = open.target;
    const QGROUPS = [
      ...QUAL_GROUPS.map((g) => ({ label: g.label, items: V[g.key] || [] })),
      { label: 'other', items: otherQualifiers },
    ].filter((g) => g.items.length);
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
        title: 'qualifier', hue: HUE.qualifier, grouped: true, options: QGROUPS,
        current: state.qualifiers[t.index]?.token,
      },
    }[t.seg];
    return (
      <VocabDropdown
        title={cfg.title} hue={cfg.hue} options={cfg.options} grouped={cfg.grouped}
        anchor={open.anchor} count={counter(t)} current={cfg.current}
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
      onClick={(e) => openDD(target, e.currentTarget)}
      title={token ? `${label} = ${token} — click to change` : `choose a ${label}`}
    >
      {token ? <span className="mono">{token}</span> : <span className="gx-tok-ph">{label}</span>}
      <svg className="gx-tok-caret" width="9" height="9" viewBox="0 0 12 12">
        <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
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
    const k = qq.kind || qualifierKind(qq.token, V);
    bar.push(chip('q' + i, k, qq.token, HUE[k] ?? HUE.qualifier, { seg: 'qualifier', index: i }));
    needSep = true;
  });
  if (state.qualifiers.length > 0 || hasConstraints) {
    bar.push(
      <button key="addq" className="gx-add-q" onClick={addGenericQualifier} title="Add another qualifier">+</button>,
    );
  }
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
    const k = qq.kind || qualifierKind(qq.token, V);
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
          {QUAL_GROUPS.map((g) => (
            <RailNode key={g.key} label={g.label} hue={HUE[g.kind]} on={hasQual(g.kind)} filled={hasQual(g.kind)}
              onToggle={() => toggleQualKind(g.kind)} title={`Toggle a ${g.label} qualifier`} />
          ))}
          <RailNode label="qualifier" hue={HUE.qualifier} on={hasQual('qualifier')} filled={hasQual('qualifier')}
            onToggle={() => toggleQualKind('qualifier')}
            title="Toggle a generic qualifier (major, external, absorbed, …); use + to add more" />
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
        <div className="gx-namebar">
          {!anySegment ? <span className="gx-name-empty">toggle a segment above to begin</span> : bar}
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

      {dropdown()}
    </div>
  );
}
