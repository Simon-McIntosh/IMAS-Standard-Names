import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../lib/data.js';

// Grammar view — a STRICT, grammar-faithful composer.
//
// This is NOT a free-form composer. It mirrors the canonical pattern from the
// IMAS Standard Names grammar specification exactly:
//
//   [<component> | <coordinate>]   (outermost prefix; mutually exclusive)
//   [<aggregation>] [<orbit>] [<population>] [<subject>]
//   <physical_base | geometric_base>            (REQUIRED; mutually exclusive)
//   [of_<object> | at_<position> | over_<region>]   (locus; connector by type)
//   [due_to_<process>]
//   …all wrapped by an optional operator (prefix `op_of_…` / postfix `…_op`).
//
// Every segment occupies one LOCKED position — there is no reordering and no
// repetition. component requires a physical base, coordinate requires a
// geometric base; component/coordinate are mutually exclusive and draw from
// the SAME `components` vocabulary (per the spec).
//
// Data comes from the catalog dataset: `GRAMMAR_VOCAB` (the closed
// vocabularies emitted by imas_standard_names/catalog/dataset.py) and the
// pre-parsed `parse[]` segments on each name (no in-browser parser).
// Seeds from / hands back to Browse.

// ---- canonical segments, in locked order --------------------------------
// `vocabKey` names the GRAMMAR_VOCAB section the segment draws from; the
// locus segment unions locus_registry + regions (see `vocabFor`). `alt`
// marks a mutually-exclusive group; `altReq` marks the group as mandatory.
const SEGS = [
  { id: 'operator', label: 'operator', hue: 320, opt: true, wrap: true, vocabKey: 'operators' },
  { id: 'component', label: 'component', hue: 200, opt: true, alt: 'proj', vocabKey: 'components' },
  { id: 'coordinate', label: 'coordinate', hue: 200, opt: true, alt: 'proj', vocabKey: 'components' },
  { id: 'aggregation', label: 'aggregation', hue: 65, opt: true, vocabKey: 'aggregations' },
  { id: 'orbit', label: 'orbit', hue: 5, opt: true, vocabKey: 'orbits' },
  { id: 'population', label: 'population', hue: 25, opt: true, vocabKey: 'populations' },
  { id: 'subject', label: 'subject', hue: 15, opt: true, vocabKey: 'subjects' },
  { id: 'physical_base', label: 'physical base', hue: 260, alt: 'base', altReq: true, vocabKey: 'physical_bases' },
  { id: 'geometric_base', label: 'geometric base', hue: 285, alt: 'base', altReq: true, vocabKey: 'geometry_carriers' },
  { id: 'locus', label: 'locus', hue: 145, opt: true, isLocus: true, vocabKey: '__locus__' },
  { id: 'process', label: 'process', hue: 290, opt: true, conn: '_due_to_', vocabKey: 'processes' },
];
const DOMAIN = { id: 'domain', label: 'domain', hue: null, opt: true, vocabKey: 'physics_domains' };
const ALL = [...SEGS, DOMAIN];
const segById = (id) => ALL.find((s) => s.id === id);
const hueOf = (s) => (s && s.hue != null ? s.hue : 250);

// physical_base ↔ component, geometric_base ↔ coordinate (each pair mutually
// exclusive). The spec's canonical pattern: <geometric_base | physical_base>.
const BASE_FOR_PROJ = { component: 'physical_base', coordinate: 'geometric_base' };
const PROJ_FOR_BASE = { physical_base: 'component', geometric_base: 'coordinate' };

// Locus relation = the LocusRef.relation in the ISN IR. Fallback when a
// registry token carries no explicit relations: entity/geometry → of,
// region → over, position → at|of (a genuine per-name choice).
const REL_BY_TYPE = { entity: ['of'], position: ['at', 'of'], geometry: ['of'], region: ['over'] };

// Token → owning segment, by descending claim priority.
const SEED_PRIORITY = [
  'physical_base', 'geometric_base', 'locus', 'component', 'operator',
  'aggregation', 'subject', 'orbit', 'population', 'process', 'domain',
];
const ROLE_DEFAULT = {
  base: 'physical_base', axis: 'component', reduction: 'operator', modifier: 'aggregation',
  operator: 'operator', subject: 'subject', locus: 'locus',
};

// Resolve a segment's vocabulary entry list from the GRAMMAR_VOCAB object.
function vocabFor(V, seg) {
  if (seg.vocabKey === '__locus__') {
    return [
      ...(V.locus_registry || []),
      ...((V.regions || []).map((r) => ({ ...r, type: 'region' }))),
    ];
  }
  return V[seg.vocabKey] || [];
}

// Flatten composed parts back to a name string. A position locus renders its
// connector as an interactive `at|of` switch (a `locusrel` part rather than a
// plain `sep`), so its `_<rel>_` connector must be re-emitted here — otherwise
// the composed name drops the connector and never round-trips to its catalog
// entry.
const partsToName = (parts) =>
  parts
    .map((p) => {
      if (p.kind === 'sep') return p.text;
      if (p.kind === 'locusrel') return `_${p.rel}_`;
      return p.token;
    })
    .filter(Boolean)
    .join('');

// ---- jump arrow (the cross-view "open in Browse" affordance) -------------
function JumpArrow() {
  return (
    <svg className="jump-arrow" width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M5 11L11 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M6 5h5v5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---- vocabulary dropdown (module-level so its search box keeps state) ----
function VocabDropdown({ seg, vocab, anchor, residual, matchConstraint, current, onChoose, onClear, onClose }) {
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
  const total = vocab.length;
  const flat = useMemo(() => {
    const out = vocab
      .filter((t) => !q || t.token.includes(q) || (t.note && t.note.toLowerCase().includes(q)))
      .map((t) => ({ t, count: residual.filter((n) => matchConstraint(n, seg.id, t.token)).length }));
    out.sort((a, b) => b.count - a.count || a.t.token.localeCompare(b.t.token));
    return out;
  }, [q, residual, vocab, matchConstraint, seg.id]);
  const W = 300;
  const H = 380;
  const left = Math.max(8, Math.min(anchor.x, window.innerWidth - W - 8));
  const top = Math.min(anchor.y + 6, window.innerHeight - H - 8);
  const Row = ({ t, count }) => (
    <button
      className={`gx-dd-row ${count > 0 ? 'is-avail' : 'is-dead'} ${current === t.token ? 'is-current' : ''}`}
      onClick={() => onChoose(t.token)}
      title={t.note || t.token}
    >
      <span className="gx-dd-tok mono">{t.token}</span>
      <span className="gx-dd-count">{count || '—'}</span>
    </button>
  );
  return (
    <div className="gx-dd" ref={ref} style={{ left, top, '--role-hue': hueOf(seg) }}>
      <div className="gx-dd-head">
        <span className="gx-dd-title">{seg.label}</span>
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
        {current && <button className="gx-dd-clear" onClick={onClear}>× clear {seg.label}</button>}
        {flat.map(({ t, count }) => <Row key={t.token} t={t} count={count} />)}
        {flat.length === 0 && <div className="gx-dd-empty">no tokens match “{term}”</div>}
      </div>
    </div>
  );
}

// ---- grammar chain (locked-order syntax diagram + toggles) ---------------
function ChainNode({ seg, on, filled, onToggle }) {
  const noTick = seg.req || seg.altReq;
  return (
    <button
      className={`gx-node ${seg.req ? 'is-req' : 'is-opt'} ${on ? 'is-on' : 'is-off'} ${filled ? 'is-filled' : ''}`}
      style={{ '--role-hue': hueOf(seg) }}
      onClick={() => { if (!seg.req) onToggle(seg.id); }}
      title={seg.altReq ? (on ? `${seg.label} — active` : `Switch to ${seg.label}`) : (on ? `Remove ${seg.label}` : `Add ${seg.label}`)}
    >
      <span className="gx-node-dot" aria-hidden />
      <span className="gx-node-label">{seg.label}</span>
      {!noTick && <span className="gx-node-tick" aria-hidden>{on ? '−' : '+'}</span>}
    </button>
  );
}

function Chain({ active, vals, onToggle }) {
  const isOn = (id) => active.has(id);
  const isFilled = (id) => !!vals[id];
  const node = (id) => {
    const s = segById(id);
    return <ChainNode key={id} seg={s} on={isOn(id)} filled={isFilled(id)} onToggle={onToggle} />;
  };
  return (
    <div className="gx-chain">
      <div className="gx-rail">
        {node('operator')}<span className="gx-rail-link" />
        {node('component')}<span className="gx-alt-pipe" aria-hidden>|</span>{node('coordinate')}<span className="gx-rail-link" />
        {node('aggregation')}<span className="gx-rail-link" />
        {node('orbit')}<span className="gx-rail-link" />
        {node('population')}<span className="gx-rail-link" />
        {node('subject')}<span className="gx-rail-link" />
        {node('physical_base')}<span className="gx-alt-pipe" aria-hidden>|</span>{node('geometric_base')}
        <span className="gx-conn mono">of_/at_/over_</span>
        {node('locus')}
        <span className="gx-conn mono">due_to_</span>
        {node('process')}
      </div>
    </div>
  );
}

// ---- composition box -----------------------------------------------------
function Composition({ parts, onOpen, openId, name, exists, onOpenInBrowse, onClear, showClear, onCycleRel }) {
  const prod = [];
  parts.forEach((p) => {
    if (p.kind === 'sep' && /[a-z]/.test(p.text)) {
      prod.push(<span key={`c${prod.length}`} className="gx-prod-conn mono">{p.text.replace(/_/g, '')}_</span>);
    }
    if (p.kind === 'locusrel') {
      prod.push(<span key={`c${prod.length}`} className="gx-prod-conn mono">{p.rel}_</span>);
    }
    if (p.kind === 'token') {
      prod.push(<span key={`t${prod.length}`} className="gx-prod-seg" style={{ '--role-hue': p.hue }}>&lt;{segById(p.segId).label}&gt;</span>);
    }
  });
  return (
    <div className="gx-comp">
      <div className="gx-comp-head">
        {name && exists
          ? <button className="gx-comp-k is-link" onClick={() => onOpenInBrowse(name)} title={`Open ${name} in Browse`}>standard name<JumpArrow /></button>
          : <span className="gx-comp-k">standard name</span>}
        {showClear && <button className="gx-clear" onClick={onClear}>clear</button>}
      </div>
      <div className="gx-namebar">
        {parts.length === 0 && <span className="gx-name-empty">pick a base to begin</span>}
        {parts.map((p, i) => {
          if (p.kind === 'locusrel') {
            return (
              <button key={i} className="gx-relsw mono" onClick={onCycleRel}
                title={`locus relation — ${p.allowed.join(' | ')} both valid for this position; click to switch`}>
                _{p.rel}_<span className="gx-relsw-cue" aria-hidden>⇅</span>
              </button>
            );
          }
          if (p.kind === 'sep') return <span key={i} className="gx-sep mono">{p.text}</span>;
          const seg = segById(p.segId);
          const filled = !!p.token;
          return (
            <button
              key={i}
              className={`gx-tok ${filled ? 'is-filled' : 'is-empty'} ${openId === p.segId ? 'is-open' : ''}`}
              style={{ '--role-hue': p.hue }}
              onClick={(e) => onOpen(seg, e.currentTarget.getBoundingClientRect())}
              title={filled ? `${seg.label} = ${p.token} — click to change` : `choose a ${seg.label}`}
            >
              {filled ? <span className="mono">{p.token}</span> : <span className="gx-tok-ph">{seg.label}</span>}
              <svg className="gx-tok-caret" width="9" height="9" viewBox="0 0 12 12"><path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          );
        })}
      </div>
      {parts.length > 0 && (
        <div className="gx-prod">
          <span className="gx-prod-k">production</span>
          <code className="gx-prod-body">{prod.length ? prod : <span className="gx-prod-seg">&lt;base&gt;</span>}</code>
        </div>
      )}
    </div>
  );
}

// ---- main ----------------------------------------------------------------
export function Grammar({ onSelect, setView, query, seedName, seedNonce }) {
  const { NAMES, GRAMMAR_VOCAB } = useData();
  const V = GRAMMAR_VOCAB || {};

  const [active, setActive] = useState(() => new Set(['physical_base']));
  const [vals, setVals] = useState({});
  const [open, setOpen] = useState(null); // { seg, anchor }

  // Parse map straight from the emitted `parse[]` segments — no in-browser
  // parser. matchConstraint is role-agnostic (text match), so the emitter's
  // role labels need not line up with the composer's segment ids.
  //
  // The emitter renders the locus segment WITH its relation connector
  // (`of_<tok>` / `at_<tok>` / `over_<tok>`); the composer matches and seeds
  // against the BARE registry token, so strip the leading connector here.
  const parseMap = useMemo(() => {
    const m = new Map();
    for (const n of NAMES) {
      const parse = (n.parse || []).map((t) =>
        t.role === 'locus' ? { ...t, text: t.text.replace(/^(?:of|at|over)_/, '') } : t,
      );
      m.set(n.name, parse);
    }
    return m;
  }, [NAMES]);

  // V-derived helpers — rebuilt only when the vocabulary changes.
  const helpers = useMemo(() => {
    const PHYS = new Set((V.physical_bases || []).map((t) => t.token));
    const GEO = new Set((V.geometry_carriers || []).map((t) => t.token));
    const locusEntry = (tok) =>
      (V.locus_registry || []).find((x) => x.token === tok)
      || ((V.regions || []).some((r) => r.token === tok) ? { token: tok, type: 'region', relations: ['over'] } : null);
    const locusRelations = (tok) => {
      const e = locusEntry(tok);
      if (!e) return ['of'];
      return (e.relations && e.relations.length) ? e.relations : (REL_BY_TYPE[e.type] || ['of']);
    };
    const pickRel = (tok, rel) => {
      const al = locusRelations(tok);
      return (rel && al.includes(rel)) ? rel : al[0];
    };

    // token → owning segment, claimed by descending priority
    const TOKEN_SEG = {};
    for (const id of SEED_PRIORITY) {
      const s = segById(id);
      for (const t of vocabFor(V, s)) if (!(t.token in TOKEN_SEG)) TOKEN_SEG[t.token] = id;
    }
    const segForSeed = (role, text) => {
      const pref = ({
        base: ['physical_base', 'geometric_base'], axis: ['component'], reduction: ['operator', 'aggregation'],
        modifier: ['aggregation', 'operator', 'subject'], operator: ['operator'], subject: ['subject'], locus: ['locus'],
      })[role] || [];
      for (const id of pref) if (vocabFor(V, segById(id)).some((t) => t.token === text)) return id;
      return TOKEN_SEG[text] || ROLE_DEFAULT[role] || null;
    };

    const composeParts = (act, v) => {
      const chain = [];
      const push = (segId, token, conn) => chain.push({ segId, token: token || null, conn });
      if (act.has('component')) push('component', v.component);
      if (act.has('coordinate')) push('coordinate', v.coordinate);
      if (act.has('aggregation')) push('aggregation', v.aggregation);
      if (act.has('orbit')) push('orbit', v.orbit);
      if (act.has('population')) push('population', v.population);
      if (act.has('subject')) push('subject', v.subject);
      const baseId = act.has('geometric_base') ? 'geometric_base' : 'physical_base';
      push(baseId, v[baseId]);
      if (act.has('locus')) {
        const tok = v.locus;
        const allowed = tok ? locusRelations(tok) : ['of'];
        const rel = pickRel(tok, v.locusRel);
        chain.push({ segId: 'locus', token: tok || null, conn: `_${rel}_`, rel, allowed });
      }
      if (act.has('process')) push('process', v.process, '_due_to_');

      const parts = [];
      chain.forEach((c, i) => {
        if (c.conn) {
          if (c.segId === 'locus' && c.allowed && c.allowed.length > 1) {
            parts.push({ kind: 'locusrel', rel: c.rel, allowed: c.allowed });
          } else {
            parts.push({ kind: 'sep', text: c.conn });
          }
        } else if (i > 0) {
          parts.push({ kind: 'sep', text: '_' });
        }
        parts.push({ kind: 'token', segId: c.segId, token: c.token, hue: hueOf(segById(c.segId)) });
      });

      if (act.has('operator')) {
        const op = v.operator;
        const od = op ? (V.operators || []).find((o) => o.token === op) : null;
        const postfix = od && od.kind === 'unary_postfix';
        const tokPart = { kind: 'token', segId: 'operator', token: op || null, hue: hueOf(segById('operator')) };
        if (postfix) {
          parts.push({ kind: 'sep', text: '_' }, tokPart);
        } else {
          parts.unshift({ kind: 'sep', text: '_of_' });
          parts.unshift(tokPart);
        }
      }
      return parts;
    };

    return { PHYS, GEO, locusEntry, locusRelations, pickRel, segForSeed, composeParts };
  }, [V]);

  const { locusRelations, pickRel, segForSeed, composeParts } = helpers;

  // n matches a constraint when its emitted parse carries the token (or, for
  // process, when the name contains the `_due_to_<token>` connector; for
  // domain, when the record's category equals the token).
  const matchConstraint = useMemo(() => (n, segId, token) => {
    if (!token) return true;
    if (segId === 'domain') return n.category === token;
    const p = parseMap.get(n.name) || [];
    if (p.some((t) => t.text === token)) return true;
    if (segId === 'process') return n.name.includes('_due_to_' + token);
    return false;
  }, [parseMap]);

  // Seed the builder from an existing name's emitted parse.
  const seedFrom = useMemo(() => (name) => {
    const a = new Set();
    const v = {};
    for (const t of (parseMap.get(name) || [])) {
      const id = segForSeed(t.role, t.text);
      if (!id) continue;
      a.add(id);
      v[id] = t.text;
    }
    if (!a.has('physical_base') && !a.has('geometric_base')) a.add('physical_base');
    if (a.has('locus') && v.locus) {
      for (const rel of ['over', 'at', 'of']) if (name.includes(`_${rel}_${v.locus}`)) { v.locusRel = rel; break; }
      if (!v.locusRel) v.locusRel = locusRelations(v.locus)[0];
    }
    // keep projection ↔ base kind consistent
    if (a.has('geometric_base') && a.has('component')) { if (v.component != null) v.coordinate = v.component; a.delete('component'); delete v.component; a.add('coordinate'); }
    if (a.has('physical_base') && a.has('coordinate')) { if (v.coordinate != null) v.component = v.coordinate; a.delete('coordinate'); delete v.coordinate; a.add('component'); }
    const m = name.match(/_due_to_(.+)$/);
    if (m) { a.add('process'); v.process = m[1]; }
    return { active: a, vals: v };
  }, [parseMap, segForSeed, locusRelations]);

  const loadName = (nm) => {
    if (!nm) return;
    const { active: a, vals: v } = seedFrom(nm);
    setActive(a);
    setVals(v);
    setOpen(null);
  };

  // Re-seed whenever Browse hands over a new selection (nonce forces a
  // re-seed even when the name is unchanged). Also keyed on `parseMap` so a
  // seed requested before the dataset finished loading applies once the
  // names arrive (parseMap is stable thereafter, so this never clobbers a
  // user's in-progress edits).
  useEffect(() => {
    if (seedName && parseMap.size) loadName(seedName);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedNonce, parseMap]);

  const constraints = useMemo(() => {
    const out = [];
    for (const id of active) if (vals[id]) out.push([id, vals[id]]);
    return out;
  }, [active, vals]);

  const q = (query || '').trim().toLowerCase();
  const results = useMemo(
    () => NAMES.filter((n) =>
      constraints.every(([id, tok]) => matchConstraint(n, id, tok))
      && (!q || n.name.includes(q) || (n.short && n.short.toLowerCase().includes(q)))),
    [NAMES, constraints, matchConstraint, q],
  );
  const residual = useMemo(() => {
    if (!open) return NAMES;
    const others = constraints.filter(([id]) => id !== open.seg.id);
    return NAMES.filter((n) => others.every(([id, tok]) => matchConstraint(n, id, tok)));
  }, [open, NAMES, constraints, matchConstraint]);

  const parts = composeParts(active, vals);
  const composed = partsToName(parts);
  const exists = composed && NAMES.some((n) => n.name === composed);

  // Keep projection (component｜coordinate) and base kind
  // (physical_base｜geometric_base) consistent: switching one switches the
  // other; component/coordinate share a vocabulary so the axis token carries.
  const couple = (changedId, a, v) => {
    if (BASE_FOR_PROJ[changedId]) {
      const need = BASE_FOR_PROJ[changedId];
      const other = need === 'physical_base' ? 'geometric_base' : 'physical_base';
      if (a.has(other)) { a.delete(other); a.add(need); }
    }
    if (PROJ_FOR_BASE[changedId]) {
      const need = PROJ_FOR_BASE[changedId];
      const other = need === 'component' ? 'coordinate' : 'component';
      if (a.has(other)) { if (v[other] != null) v[need] = v[other]; a.delete(other); delete v[other]; a.add(need); }
    }
  };

  const toggle = (id) => {
    const seg = segById(id);
    const a = new Set(active);
    const v = { ...vals };
    const sibs = seg.alt ? SEGS.filter((s) => s.alt === seg.alt) : [];
    const required = sibs.some((s) => s.altReq);
    if (a.has(id)) {
      if (required) return; // exactly one base is mandatory
      a.delete(id);
      delete v[id];
      if (open && open.seg.id === id) setOpen(null);
    } else {
      for (const s of sibs) {
        if (s.id !== id && a.has(s.id)) {
          if (seg.alt === 'proj' && v[s.id] != null) v[id] = v[s.id]; // carry axis token
          a.delete(s.id);
          if (seg.alt !== 'base') delete v[s.id]; // keep the other base's token as memory
        }
      }
      a.add(id);
      couple(id, a, v);
    }
    setActive(a);
    setVals(v);
  };

  const openDD = (seg, rect) => {
    if (open && open.seg.id === seg.id) { setOpen(null); return; }
    setOpen({ seg, anchor: { x: rect.left, y: rect.bottom } });
  };

  const choose = (token) => {
    const seg = open.seg;
    const a = new Set(active);
    const v = { ...vals, [seg.id]: token };
    if (seg.id === 'locus') v.locusRel = locusRelations(token)[0];
    if (!a.has(seg.id)) a.add(seg.id);
    setActive(a);
    setVals(v);
    setOpen(null);
  };

  const cycleLocusRel = () => {
    const tok = vals.locus;
    if (!tok) return;
    const al = locusRelations(tok);
    if (al.length < 2) return;
    const cur = pickRel(tok, vals.locusRel);
    setVals((v) => ({ ...v, locusRel: al[(al.indexOf(cur) + 1) % al.length] }));
  };

  const clearVal = () => {
    const seg = open.seg;
    const v = { ...vals };
    delete v[seg.id];
    if (seg.id === 'locus') delete v.locusRel;
    setVals(v);
    setOpen(null);
  };
  const clearAll = () => {
    setActive(new Set(['physical_base']));
    setVals({});
    setOpen(null);
  };

  const openVocab = open ? vocabFor(V, open.seg) : [];

  return (
    <div className="grammar-view" data-active-view="grammar">
      <Chain active={active} vals={vals} onToggle={toggle} />
      <Composition
        parts={parts}
        onOpen={openDD}
        openId={open && open.seg.id}
        name={composed}
        exists={exists}
        onOpenInBrowse={(nm) => { onSelect(nm); setView('browse'); }}
        onClear={clearAll}
        showClear={constraints.length > 0}
        onCycleRel={cycleLocusRel}
      />

      <div className="gx-results">
        <div className="gx-results-meta">
          <strong>{results.length}</strong> {results.length === 1 ? 'name' : 'names'}
          {constraints.length ? ' match this composition' : ' in the catalog'}
          {q ? <> · filtered by “{query.trim()}”</> : null}
        </div>
        {results.length === 0 ? (
          <div className="gx-empty">No catalogued name matches this combination — the composition is grammatically valid but not yet in the catalog.</div>
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

      {open && (
        <VocabDropdown
          seg={open.seg}
          vocab={openVocab}
          anchor={open.anchor}
          residual={residual}
          matchConstraint={matchConstraint}
          current={vals[open.seg.id]}
          onChoose={choose}
          onClear={clearVal}
          onClose={() => setOpen(null)}
        />
      )}
    </div>
  );
}
