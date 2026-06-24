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
// It mirrors the ISN grammar exactly (see lib/grammar-compose.js, a JS mirror
// of imas_standard_names/grammar/render.py): a name decomposes into an
// optional operator, an optional projection axis, an ORDERED list of
// qualifiers, a required base, an optional locus, and an optional mechanism.
// Seeding reads a name's authoritative emitted `parse[]` (no in-browser
// parser, no vocabulary guessing) and the composition reconstructs the name
// verbatim — every catalogue name round-trips. Seeds from / hands back to
// Browse.

// Role hues — match the Browse parse-breakdown colours.
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

// Qualifier sub-kinds get their own rail node (matching the grammar's
// colour language); the generic "qualifier" node covers everything else.
// `group` keys map to a GRAMMAR_VOCAB section and to the qualifierKind label.
const QUAL_GROUPS = [
  { key: 'aggregations', kind: 'aggregation', label: 'aggregation' },
  { key: 'orbits', kind: 'orbit', label: 'orbit' },
  { key: 'populations', kind: 'population', label: 'population' },
  { key: 'subjects', kind: 'subject', label: 'subject' },
];

// Locus token → allowed relations (of / at / over), from the registry.
function locusRelationsFor(vocab, token) {
  const reg = (vocab.locus_registry || []).find((x) => x.token === token);
  if (reg) return reg.relations && reg.relations.length ? reg.relations : REL_BY_TYPE[reg.type] || ['of'];
  if ((vocab.regions || []).some((r) => r.token === token)) return ['over'];
  return ['of'];
}

// ---- jump arrow (cross-view affordance) ----------------------------------
function JumpArrow() {
  return (
    <svg className="jump-arrow" width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M5 11L11 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M6 5h5v5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---- vocabulary dropdown (module-level so its search box keeps state) ----
// `options` is either a flat list of {token, note?} or a list of groups
// {label, items:[{token, note?}]}. `count(token)` returns the catalog usage.
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
  const match = (t) => !q || t.token.includes(q) || (t.note && t.note.toLowerCase().includes(q));
  const score = (items) =>
    items
      .filter(match)
      .map((t) => ({ t, c: count(t.token) }))
      .sort((a, b) => b.c - a.c || a.t.token.localeCompare(b.t.token));

  const total = grouped
    ? options.reduce((a, g) => a + g.items.length, 0)
    : options.length;
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
      <input
        className="gx-dd-search mono"
        autoFocus
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        placeholder="filter vocabulary…"
        spellCheck="false"
      />
      <div className="gx-dd-list">
        {current && <button className="gx-dd-clear" onClick={onClear}>× clear</button>}
        {groups &&
          groups.map((g) => (
            <div key={g.label} className="gx-dd-group">
              <div className="gx-dd-grouph">
                {g.label}
                <span className="gx-dd-groupn">{g.rows.length}</span>
              </div>
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

// ---- chain rail: locked-order syntax diagram ------------------------------
function RailNode({ label, hue, on, filled, optional, onClick, title }) {
  return (
    <button
      className={`gx-node ${optional ? 'is-opt' : 'is-req'} ${on ? 'is-on' : 'is-off'} ${filled ? 'is-filled' : ''}`}
      style={{ '--role-hue': hue }}
      onClick={onClick}
      title={title}
    >
      <span className="gx-node-dot" aria-hidden />
      <span className="gx-node-label">{label}</span>
      {optional && <span className="gx-node-tick" aria-hidden>{on ? '−' : '+'}</span>}
    </button>
  );
}

// ---- main ----------------------------------------------------------------
export function Grammar({ onSelect, setView, query, seedName, seedNonce }) {
  const { NAMES, GRAMMAR_VOCAB } = useData();
  const V = GRAMMAR_VOCAB || {};

  const [state, setState] = useState(emptyState);
  const [open, setOpen] = useState(null); // { target, anchor }

  // Pre-decompose every catalogue name once (role-driven, authoritative).
  const nameStates = useMemo(() => {
    const m = new Map();
    for (const n of NAMES) m.set(n.name, seedFromParse(n.parse, V, n.name));
    return m;
  }, [NAMES, V]);

  // Seed from a name's authoritative parse — verbatim round-trip guaranteed.
  const loadName = (nm) => {
    if (!nm) return;
    const ns = nameStates.get(nm);
    setState(ns ? structuredClone(ns) : emptyState());
    setOpen(null);
  };

  // Re-seed when Browse hands over a selection (nonce forces re-seed even on
  // the same name); also keyed on nameStates so a seed requested before the
  // dataset loaded applies once names arrive.
  useEffect(() => {
    if (seedName && nameStates.size) loadName(seedName);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedNonce, nameStates]);

  const composed = composeName(state);
  const exists = composed && nameStates.has(composed);

  // Grouped qualifier vocabulary: sub-kinds first, then everything else.
  const qualifierGroups = useMemo(() => {
    const sub = ['aggregations', 'orbits', 'populations', 'subjects'];
    const claimed = new Set();
    const groups = [];
    const labels = {
      aggregations: 'Aggregation',
      orbits: 'Orbit',
      populations: 'Population',
      subjects: 'Subject',
    };
    for (const key of sub) {
      const items = V[key] || [];
      items.forEach((t) => claimed.add(t.token));
      if (items.length) groups.push({ label: labels[key], items });
    }
    const other = (V.qualifiers || []).filter((t) => !claimed.has(t.token));
    if (other.length) groups.push({ label: 'Other', items: other });
    return groups;
  }, [V]);

  // Generic qualifiers — those not covered by a named sub-kind node.
  const otherQualifiers = useMemo(() => {
    const claimed = new Set();
    for (const g of QUAL_GROUPS) (V[g.key] || []).forEach((t) => claimed.add(t.token));
    return (V.qualifiers || []).filter((t) => !claimed.has(t.token));
  }, [V]);

  // Constraint-filtered results (AND across every filled slot).
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

  // Residual corpus for dropdown counts (all constraints except the open one).
  const residual = useMemo(() => {
    if (!open) return NAMES;
    const probe = { ...state };
    switch (open.target.kind) {
      case 'operator': probe.operator = null; break;
      case 'projection': probe.axis = null; break;
      case 'base': probe.base = null; break;
      case 'locus': probe.locus = null; break;
      case 'process': probe.mechanism = null; break;
      case 'qualifier-edit':
        probe.qualifiers = state.qualifiers.filter((_, i) => i !== open.target.index);
        break;
      default: break; // qualifier-add keeps all current constraints
    }
    return NAMES.filter((n) => matchesComposition(nameStates.get(n.name), probe));
  }, [open, NAMES, nameStates, state]);

  // Count of residual names carrying `token` in the open slot's role.
  const counter = (target) => (token) => {
    let key;
    switch (target.kind) {
      case 'operator': key = (ns) => ns.operator?.token === token; break;
      case 'projection': key = (ns) => ns.axis === token; break;
      case 'base': key = (ns) => ns.base?.token === token; break;
      case 'locus': key = (ns) => ns.locus?.token === token; break;
      case 'process': key = (ns) => ns.mechanism === token; break;
      default: key = (ns) => (ns.qualifiers || []).includes(token); // qualifier add/edit
    }
    return residual.filter((n) => key(nameStates.get(n.name) || {})).length;
  };

  // ---- mutations ---------------------------------------------------------
  const openDD = (target, el) => {
    const r = el.getBoundingClientRect();
    setOpen((o) =>
      o &&
      o.target.kind === target.kind &&
      o.target.index === target.index &&
      o.target.group === target.group
        ? null
        : { target, anchor: { x: r.left, y: r.bottom } },
    );
  };

  // Is a qualifier of the given sub-kind ('aggregation'|'orbit'|… |'qualifier')
  // currently in the ordered list? Drives rail-node on/filled state.
  const hasQual = (kind) => state.qualifiers.some((q) => qualifierKind(q, V) === kind);

  const choose = (token) => {
    const t = open.target;
    setState((s) => {
      const next = { ...s, qualifiers: [...s.qualifiers] };
      switch (t.kind) {
        case 'operator': {
          const o = (V.operators || []).find((x) => x.token === token);
          next.operator = { token, kind: o ? o.kind : 'unary_prefix' };
          break;
        }
        case 'projection': next.axis = token; break;
        case 'base': {
          const kind =
            t.baseKind ||
            ((V.physical_bases || []).some((b) => b.token === token) ? 'physical' : 'geometric');
          next.base = { token, kind };
          break;
        }
        case 'locus':
          next.locus = { token, relation: locusRelationsFor(V, token)[0] };
          break;
        case 'process': next.mechanism = token; break;
        case 'qualifier-add': {
          // A named sub-kind is single-occurrence: replace the existing
          // qualifier of that kind in place (preserving order); the generic
          // "other" group appends, since multiple plain qualifiers are valid.
          const subKind = QUAL_GROUPS.find((g) => g.key === t.group)?.kind;
          const idx = subKind
            ? next.qualifiers.findIndex((q) => qualifierKind(q, V) === subKind)
            : -1;
          if (idx >= 0) next.qualifiers[idx] = token;
          else next.qualifiers.push(token);
          break;
        }
        case 'qualifier-edit': next.qualifiers[t.index] = token; break;
        default: break;
      }
      return next;
    });
    setOpen(null);
  };

  const clearSlot = () => {
    const t = open.target;
    setState((s) => {
      const next = { ...s, qualifiers: [...s.qualifiers] };
      switch (t.kind) {
        case 'operator': next.operator = null; break;
        case 'projection': next.axis = null; break;
        case 'base': next.base = null; break;
        case 'locus': next.locus = null; break;
        case 'process': next.mechanism = null; break;
        case 'qualifier-edit': next.qualifiers.splice(t.index, 1); break;
        default: break;
      }
      return next;
    });
    setOpen(null);
  };

  const cycleLocusRel = () => {
    setState((s) => {
      if (!s.locus) return s;
      const al = locusRelationsFor(V, s.locus.token);
      if (al.length < 2) return s;
      const i = al.indexOf(s.locus.relation);
      return { ...s, locus: { ...s.locus, relation: al[(i + 1) % al.length] } };
    });
  };

  const clearAll = () => {
    setState(emptyState());
    setOpen(null);
  };

  // ---- dropdown config for the open target -------------------------------
  const dropdown = () => {
    if (!open) return null;
    const t = open.target;
    const group = QUAL_GROUPS.find((g) => g.key === t.group);
    const cfg = {
      operator: { title: 'operator', hue: HUE.operator, options: V.operators || [], current: state.operator?.token },
      projection: {
        title: t.baseKind === 'geometric' ? 'coordinate' : 'component',
        hue: HUE.projection,
        options: V.components || [],
        current: state.axis,
      },
      base: {
        title: t.baseKind === 'geometric' ? 'geometric base' : 'physical base',
        hue: t.baseKind === 'geometric' ? HUE.base_geometric : HUE.base_physical,
        options: t.baseKind === 'geometric' ? V.geometry_carriers || [] : V.physical_bases || [],
        current: state.base?.token,
      },
      locus: {
        title: 'locus',
        hue: HUE.locus,
        options: [...(V.locus_registry || []), ...(V.regions || [])],
        current: state.locus?.token,
      },
      process: { title: 'process', hue: HUE.process, options: V.processes || [], current: state.mechanism },
      'qualifier-add': group
        ? { title: group.label, hue: HUE[group.kind], options: V[group.key] || [], current: null }
        : { title: 'qualifier', hue: HUE.qualifier, options: otherQualifiers, current: null },
      'qualifier-edit': {
        title: 'qualifier',
        hue: HUE.qualifier,
        grouped: true,
        options: qualifierGroups,
        current: state.qualifiers[t.index],
      },
    }[t.kind];
    return (
      <VocabDropdown
        title={cfg.title}
        hue={cfg.hue}
        options={cfg.options}
        grouped={cfg.grouped}
        anchor={open.anchor}
        count={counter(t)}
        current={cfg.current}
        onChoose={choose}
        onClear={clearSlot}
        onClose={() => setOpen(null)}
      />
    );
  };

  // ---- composition bar parts ---------------------------------------------
  // Each token chip in canonical order; qualifiers are coloured per sub-kind.
  const isPostfix = state.operator?.kind === 'unary_postfix';

  const tokChip = (key, label, token, hue, target) => (
    <button
      key={key}
      className={`gx-tok ${token ? 'is-filled' : 'is-empty'} ${open && open.target.kind === target.kind && open.target.index === target.index ? 'is-open' : ''}`}
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

  const barParts = [];
  let needSep = false;
  const pushSep = (k) => { if (needSep) barParts.push(sep(k, '_')); };

  // operator prefix
  if (state.operator && !isPostfix) {
    barParts.push(tokChip('op', 'operator', state.operator.token, HUE.operator, { kind: 'operator' }));
    barParts.push(sep('opsep', '_of_'));
    needSep = false;
  }
  // projection axis
  if (state.axis) {
    pushSep('axsep');
    barParts.push(tokChip('axis', 'component', state.axis, HUE.projection, { kind: 'projection' }));
    needSep = true;
  }
  // qualifiers (ordered, per-kind colour)
  state.qualifiers.forEach((tok, i) => {
    pushSep('qs' + i);
    barParts.push(
      tokChip('q' + i, 'qualifier', tok, HUE[qualifierKind(tok, V)] ?? HUE.qualifier, {
        kind: 'qualifier-edit',
        index: i,
      }),
    );
    needSep = true;
  });
  // base (required)
  pushSep('bsep');
  barParts.push(
    tokChip(
      'base',
      'base',
      state.base?.token,
      state.base?.kind === 'geometric' ? HUE.base_geometric : HUE.base_physical,
      { kind: 'base' },
    ),
  );
  needSep = true;
  // locus (relation switch + token)
  if (state.locus) {
    const allowed = locusRelationsFor(V, state.locus.token);
    if (allowed.length > 1) {
      barParts.push(
        <button
          key="rel"
          className="gx-relsw mono"
          onClick={cycleLocusRel}
          title={`locus relation — ${allowed.join(' | ')} valid here; click to switch`}
        >
          _{state.locus.relation}_<span className="gx-relsw-cue" aria-hidden>⇅</span>
        </button>,
      );
    } else {
      barParts.push(sep('relsep', `_${state.locus.relation}_`));
    }
    barParts.push(tokChip('locus', 'locus', state.locus.token, HUE.locus, { kind: 'locus' }));
    needSep = true;
  }
  // mechanism (process)
  if (state.mechanism) {
    barParts.push(sep('mechsep', '_due_to_'));
    barParts.push(tokChip('mech', 'process', state.mechanism, HUE.process, { kind: 'process' }));
    needSep = true;
  }
  // operator postfix
  if (state.operator && isPostfix) {
    barParts.push(sep('opsep2', '_'));
    barParts.push(tokChip('op', 'operator', state.operator.token, HUE.operator, { kind: 'operator' }));
  }

  // ---- production line ----------------------------------------------------
  const prod = [];
  const prodConn = (k, txt) => prod.push(<span key={k} className="gx-prod-conn mono">{txt}</span>);
  const prodSeg = (k, label, hue) => prod.push(<span key={k} className="gx-prod-seg" style={{ '--role-hue': hue }}>&lt;{label}&gt;</span>);
  if (state.operator && !isPostfix) { prodSeg('po', 'operator', HUE.operator); prodConn('poc', 'of_'); }
  if (state.axis) prodSeg('pa', 'component', HUE.projection);
  state.qualifiers.forEach((tok, i) => prodSeg('pq' + i, qualifierKind(tok, V), HUE[qualifierKind(tok, V)] ?? HUE.qualifier));
  prodSeg('pb', state.base?.kind === 'geometric' ? 'geometric base' : 'base', state.base?.kind === 'geometric' ? HUE.base_geometric : HUE.base_physical);
  if (state.locus) { prodConn('plc', `${state.locus.relation}_`); prodSeg('pl', 'locus', HUE.locus); }
  if (state.mechanism) { prodConn('pmc', 'due_to_'); prodSeg('pm', 'process', HUE.process); }
  if (state.operator && isPostfix) prodSeg('po2', 'operator', HUE.operator);

  // ---- render -------------------------------------------------------------
  return (
    <div className="grammar-view" data-active-view="grammar">
      <div className="gx-chain">
        <div className="gx-rail">
          <RailNode label="operator" hue={HUE.operator} optional on={!!state.operator} filled={!!state.operator}
            onClick={(e) => openDD({ kind: 'operator' }, e.currentTarget)} title="Operator (prefix / postfix)" />
          <span className="gx-rail-link" />
          <RailNode label="component" hue={HUE.projection} optional
            on={!!state.axis && state.base?.kind !== 'geometric'} filled={!!state.axis}
            onClick={(e) => openDD({ kind: 'projection', baseKind: 'physical' }, e.currentTarget)}
            title="Vector component (projection of a physical base)" />
          <span className="gx-alt-pipe" aria-hidden>|</span>
          <RailNode label="coordinate" hue={HUE.projection} optional
            on={!!state.axis && state.base?.kind === 'geometric'} filled={!!state.axis}
            onClick={(e) => openDD({ kind: 'projection', baseKind: 'geometric' }, e.currentTarget)}
            title="Coordinate (projection of a geometric base)" />
          <span className="gx-rail-link" />
          {QUAL_GROUPS.map((g) => (
            <RailNode key={g.key} label={g.label} hue={HUE[g.kind]} optional
              on={hasQual(g.kind)} filled={hasQual(g.kind)}
              onClick={(e) => openDD({ kind: 'qualifier-add', group: g.key }, e.currentTarget)}
              title={`Add ${g.label} qualifier`} />
          ))}
          <RailNode label="qualifier" hue={HUE.qualifier} optional
            on={hasQual('qualifier')} filled={hasQual('qualifier')}
            onClick={(e) => openDD({ kind: 'qualifier-add' }, e.currentTarget)}
            title="Add any other qualifier (e.g. major, external, absorbed)" />
          <span className="gx-rail-link" />
          <RailNode label="physical base" hue={HUE.base_physical}
            on={state.base?.kind === 'physical'} filled={state.base?.kind === 'physical'}
            onClick={(e) => openDD({ kind: 'base', baseKind: 'physical' }, e.currentTarget)}
            title="Physical base quantity (required: pick one base)" />
          <span className="gx-alt-pipe" aria-hidden>|</span>
          <RailNode label="geometric base" hue={HUE.base_geometric}
            on={state.base?.kind === 'geometric'} filled={state.base?.kind === 'geometric'}
            onClick={(e) => openDD({ kind: 'base', baseKind: 'geometric' }, e.currentTarget)}
            title="Geometric carrier base (required: pick one base)" />
          <span className="gx-conn mono">of_/at_/over_</span>
          <RailNode label="locus" hue={HUE.locus} optional on={!!state.locus} filled={!!state.locus}
            onClick={(e) => openDD({ kind: 'locus' }, e.currentTarget)} title="Locus (object / position / region)" />
          <span className="gx-conn mono">due_to_</span>
          <RailNode label="process" hue={HUE.process} optional on={!!state.mechanism} filled={!!state.mechanism}
            onClick={(e) => openDD({ kind: 'process' }, e.currentTarget)} title="Mechanism (due_to)" />
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
          {!state.base && state.qualifiers.length === 0 && !state.axis ? (
            <span className="gx-name-empty">pick a base to begin</span>
          ) : (
            barParts
          )}
        </div>
        {(state.base || state.qualifiers.length || state.axis) && (
          <div className="gx-prod">
            <span className="gx-prod-k">production</span>
            <code className="gx-prod-body">{prod}</code>
          </div>
        )}
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
                <button
                  className={`gx-name mono ${n.name === composed ? 'is-hit' : ''}`}
                  onClick={() => loadName(n.name)}
                  title={`Load ${n.name} into the builder`}
                >
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
