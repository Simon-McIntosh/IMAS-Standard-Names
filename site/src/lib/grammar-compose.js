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

// The composer's editable state. `qualifiers` is an ordered list — this is
// the key fidelity fix: the ISN grammar's qualifier group is an arbitrary
// ordered sequence (e.g. total · external · heating), not a fixed set of
// aggregation/orbit/population/subject slots.
export function emptyState() {
  return {
    operator: null, // { token, kind }
    axis: null, // projection token
    qualifiers: [], // ordered list of tokens
    base: null, // { token, kind: 'physical' | 'geometric' }
    locus: null, // { token, relation: 'of' | 'at' | 'over' }
    mechanism: null, // process token
    raw: null, // verbatim fallback for unparseable names
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
  return 'qualifier';
}

// Seed editable state from a name's emitted `parse[]` — role-driven, no
// vocabulary guessing. Roles map 1:1 to grammar positions; every qualifier
// sub-role (aggregation/orbit/population/subject) and the generic
// `qualifier` role all append to the ordered qualifier list, preserving
// parse order so the name reconstructs verbatim.
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
        state.axis = text;
        break;
      case 'aggregation':
      case 'orbit':
      case 'population':
      case 'subject':
      case 'qualifier':
      case 'modifier':
      case 'reduction':
        if (text) state.qualifiers.push(text);
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
          ? { relation: m[1], token: m[2] }
          : { relation: 'of', token: text.replace(/^(?:of|at|over)_/, '') };
        break;
      }
      case 'process':
      case 'mechanism':
        state.mechanism = text.replace(/^due_to_/, '');
        break;
      case 'unparseable':
        state.raw = text;
        break;
      default:
        // Any unexpected role with text is preserved as a qualifier rather
        // than dropped, so the name still round-trips.
        if (text) state.qualifiers.push(text);
    }
  }

  // Fidelity guarantee: if the seeded segments don't reconstruct the exact
  // name (the parse was lossy — e.g. a BINARY operator whose operands the
  // emitter collapses to a `placeholder` base), fall back to the verbatim
  // name. The composer then DISPLAYS the true name rather than fabricating a
  // different one; the (non-decomposable) chain is simply not editable.
  if (name != null && composeName(state) !== name) {
    state.raw = name;
  }
  return state;
}

// Reconstruct the canonical name from editable state — a faithful mirror of
// render.py's `compose`. Round-trips any state produced by `seedFromParse`.
export function composeName(state) {
  if (state.raw != null) return state.raw;

  const parts = [];
  if (state.axis) parts.push(state.axis);
  if (state.qualifiers && state.qualifiers.length) parts.push(state.qualifiers.join('_'));
  if (state.base && state.base.token) parts.push(state.base.token);
  let core = parts.join('_');

  if (state.locus && state.locus.token) {
    core += `_${state.locus.relation || 'of'}_${state.locus.token}`;
  }
  if (state.mechanism) core += `_due_to_${state.mechanism}`;

  if (state.operator && state.operator.token) {
    const { token, kind } = state.operator;
    if (kind === 'unary_postfix') core = `${core}_${token}`;
    else core = `${token}_of_${core}`; // unary_prefix (and binary fallback)
  }
  return core;
}

// Does a candidate name's decomposed state satisfy every FILLED slot of the
// builder state? Drives the "names matching this composition" result list:
// each filled segment is an AND constraint; an empty builder matches all.
export function matchesComposition(nameState, builder) {
  if (!nameState) return false;
  if (builder.operator && nameState.operator?.token !== builder.operator.token) {
    return false;
  }
  if (builder.axis && nameState.axis !== builder.axis) return false;
  for (const q of builder.qualifiers || []) {
    if (!(nameState.qualifiers || []).includes(q)) return false;
  }
  if (builder.base?.token && nameState.base?.token !== builder.base.token) {
    return false;
  }
  if (builder.locus?.token && nameState.locus?.token !== builder.locus.token) {
    return false;
  }
  if (builder.mechanism && nameState.mechanism !== builder.mechanism) return false;
  return true;
}
