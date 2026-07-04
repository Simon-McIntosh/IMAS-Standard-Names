// Grammar role metadata.
//
// This module has NO parsing logic. The SPA consumes `name.parse[]` from
// the dataset emitter; we only attach human-readable role labels, hue
// values for colour-coding, and one-line descriptions used as default
// notes when a token doesn't carry its own.

// Role taxonomy. Must include every `role` value the Python dataset
// emitter produces (see `imas_standard_names/catalog/dataset.py`:
// `_derive_grammar_facets`). When a new role is added in the emitter,
// it must also be added here — otherwise the SPA falls back to
// "Unknown" for that token.
// `filterable: true` marks a role the dataset emitter produces AND that the
// UI can turn into a facet filter. This flag is the SINGLE SOURCE OF TRUTH
// for the filterable-role set — App, Filters, ParseBreakdown, and the active
// strip all derive from `FILTERABLE_PARSE_ROLES` below rather than keeping
// their own hand-copied lists (which drifted: the qualifier chip lost its
// '+' glyph and half the roles toggled filters that were never applied).
export const ROLE_META = {
  // Emitted by the current dataset builder — all filterable except
  // `unparseable` (a filter on "couldn't parse" is not a useful facet):
  operator:    { label: 'Operator',    hue: 320, desc: 'Operator applied to a base quantity', filterable: true },
  axis:        { label: 'Axis',        hue: 200, desc: 'Vector component direction', filterable: true },
  qualifier:   { label: 'Qualifier',   hue: 35,  desc: 'Qualifier scoping the quantity', filterable: true },
  aggregation: { label: 'Aggregation', hue: 345, desc: 'Population/species/contribution reduction (total, net)', filterable: true },
  orbit:       { label: 'Orbit',       hue: 5,   desc: 'Particle orbit / transit class (trapped, co-passing, …)', filterable: true },
  population:  { label: 'Population',   hue: 25,  desc: 'Species population kind/state (fast, thermal, cold, …)', filterable: true },
  zone:        { label: 'Zone',         hue: 95,  desc: 'Plasma-region / geometric sub-selector (core, edge, upper, outer, …)', filterable: true },
  channel_qualifier: { label: 'Channel qualifier', hue: 135, desc: 'Qualifier that binds to the transport channel (kinetic, plasma, diamagnetic)', filterable: true },
  channel:     { label: 'Channel',      hue: 175, desc: 'Transport channel — what is transported (heat, particle, energy, momentum)', filterable: true },
  base:        { label: 'Base',        hue: 260, desc: 'Root quantity from the canonical vocabulary', filterable: true },
  locus:       { label: 'Locus',       hue: 145, desc: 'Geometric or topological location', filterable: true },
  process:     { label: 'Process',     hue: 105, desc: 'Mechanism the quantity is due to', filterable: true },
  subject:     { label: 'Subject',     hue: 15,  desc: 'Entity the quantity applies to', filterable: true },
  unparseable: { label: 'Unparseable', hue: 0,   desc: 'Parser could not decompose this name' },

  // Reserved for future emitter use / hand-authored examples. NOT flagged
  // filterable: the emitter never produces them, so a filter key would be a
  // permanent no-op. Add `filterable: true` only when the emitter starts
  // emitting the role.
  reduction:   { label: 'Reduction',   hue: 65,  desc: 'Aggregation applied to a base quantity' },
  modifier:    { label: 'Modifier',    hue: 35,  desc: 'Qualifier scoping the quantity' },
  preposition: { label: 'Preposition', hue: 0,   desc: 'Grammatical connector' },
  unknown:     { label: 'Unknown',     hue: 0,   desc: 'Not recognised by the parser vocabulary' },
};

// Every emitted, filterable parse role — derived from ROLE_META so a new
// emitter role only needs the `filterable` flag added above. Consumers must
// import THIS rather than re-listing role names.
export const FILTERABLE_PARSE_ROLES = Object.keys(ROLE_META).filter(
  (k) => ROLE_META[k].filterable,
);

