// Faithful Standard-Name composition — a JS mirror of the ISN Python
// renderer (`imas_standard_names/grammar/render.py::compose`).
//
// The Grammar composer MUST follow the exact ISN grammar so every catalogue
// name round-trips: seed the builder from a name's authoritative emitted
// `parse[]` segments, and reconstruct the name with `composeName`. There is
// NO in-browser parser and NO vocabulary guessing — the emitted parse roles
// are taken as ground truth.
//
// Canonical form (render.py):
//   operators-wrap( join([<axis>, <qualifiers…>, <base>], "_")
//                   + "_<relation>_<locus>"
//                   + "_due_to_<mechanism>" )
// where qualifiers are joined in PARSE ORDER, and a unary-prefix operator
// renders `<op>_of_<inner>` while a unary-postfix operator renders
// `<inner>_<op>`.
//
// State shape — every segment is an object (or null = absent). A present
// segment whose `token` is null is an EMPTY slot: the rail toggled it on but
// no token is chosen yet. Empty slots contribute nothing to the composed
// name and impose no filter constraint; they only drive the editable chips.
//   operator:   null | { token, kind }            kind: unary_prefix|unary_postfix|binary
//   axis:       null | { token }                  projection
//   qualifiers: [ { token, kind } ]               ordered; kind = sub-kind for colour
//   base:       null | { token, kind }            kind: physical|geometric
//   locus:      null | { token, relation }        relation: of|at|over
//   mechanism:  null | { token }                  process
//   raw:        null | string                     verbatim fallback (lossy parses)

export function emptyState() {
  return {
    operator: null,
    axis: null,
    qualifiers: [],
    base: null,
    locus: null,
    mechanism: null,
    raw: null,
  };
}

// Classify a qualifier token into its sub-kind for colour-coding. All are
// genuine qualifiers in the grammar; the sub-kind is purely presentational.
export function qualifierKind(token, vocab) {
  const has = (key) => (vocab[key] || []).some((t) => t.token === token);
  if (has('aggregations')) return 'aggregation';
  if (has('orbits')) return 'orbit';
  if (has('populations')) return 'population';
  if (has('subjects')) return 'subject';
  if (has('zones')) return 'zone';
  if (has('channels')) return 'channel';
  return 'qualifier';
}

// Seed editable state from a name's emitted `parse[]` — role-driven, no
// vocabulary guessing. Every qualifier sub-role and the generic `qualifier`
// role append to the ordered qualifier list in parse order.
export function seedFromParse(parse, vocab, name) {
  const state = emptyState();
  const opByToken = new Map((vocab.operators || []).map((o) => [o.token, o]));
  const physical = new Set((vocab.physical_bases || []).map((b) => b.token));
  const geometric = new Set((vocab.geometry_carriers || []).map((b) => b.token));

  for (const seg of parse || []) {
    const text = seg.text || '';
    switch (seg.role) {
      case 'operator': {
        const o = opByToken.get(text);
        state.operator = { token: text, kind: o ? o.kind : 'unary_prefix' };
        break;
      }
      case 'axis':
        state.axis = { token: text };
        break;
      case 'aggregation':
      case 'orbit':
      case 'population':
      case 'subject':
      case 'zone':
      case 'channel':
      case 'qualifier':
      case 'modifier':
      case 'reduction':
        if (text) state.qualifiers.push({ token: text, kind: qualifierKind(text, vocab) });
        break;
      case 'base':
        state.base = {
          token: text,
          kind: geometric.has(text) && !physical.has(text) ? 'geometric' : 'physical',
        };
        break;
      case 'locus': {
        const m = text.match(/^(of|at|over)_(.+)$/);
        state.locus = m
          ? { token: m[2], relation: m[1] }
          : { token: text.replace(/^(?:of|at|over)_/, ''), relation: 'of' };
        break;
      }
      case 'process':
      case 'mechanism':
        state.mechanism = { token: text.replace(/^due_to_/, '') };
        break;
      case 'unparseable':
        state.raw = text;
        break;
      default:
        if (text) state.qualifiers.push({ token: text, kind: qualifierKind(text, vocab) });
    }
  }

  // Fidelity guarantee: if the seeded segments don't reconstruct the exact
  // name (a lossy parse — e.g. a BINARY operator whose operands the emitter
  // collapses to a `placeholder` base), fall back to the verbatim name so the
  // composer DISPLAYS the true name rather than fabricating a different one.
  if (name != null && composeName(state) !== name) state.raw = name;
  return state;
}

// Reconstruct the canonical name from editable state — a faithful mirror of
// render.py's `compose`. Empty (token-null) slots are skipped.
export function composeName(state) {
  if (state.raw != null) return state.raw;

  const parts = [];
  if (state.axis?.token) parts.push(state.axis.token);
  const quals = state.qualifiers.map((q) => q.token).filter(Boolean);
  if (quals.length) parts.push(quals.join('_'));
  if (state.base?.token) parts.push(state.base.token);
  let core = parts.join('_');

  if (state.locus?.token) core += `_${state.locus.relation || 'of'}_${state.locus.token}`;
  if (state.mechanism?.token) core += `_due_to_${state.mechanism.token}`;

  if (state.operator?.token) {
    const { token, kind } = state.operator;
    if (kind === 'unary_postfix') core = `${core}_${token}`;
    else core = `${token}_of_${core}`; // unary_prefix (and binary fallback)
  }
  return core;
}

// Does a candidate name's decomposed state satisfy every FILLED slot of the
// builder? Empty slots impose no constraint; an empty builder matches all.
export function matchesComposition(nameState, builder) {
  if (!nameState) return false;
  if (builder.operator?.token && nameState.operator?.token !== builder.operator.token) {
    return false;
  }
  if (builder.axis?.token && nameState.axis?.token !== builder.axis.token) return false;
  for (const q of builder.qualifiers || []) {
    if (q.token && !(nameState.qualifiers || []).some((n) => n.token === q.token)) return false;
  }
  if (builder.base?.token && nameState.base?.token !== builder.base.token) return false;
  if (builder.locus?.token && nameState.locus?.token !== builder.locus.token) return false;
  if (builder.mechanism?.token && nameState.mechanism?.token !== builder.mechanism.token) {
    return false;
  }
  return true;
}
