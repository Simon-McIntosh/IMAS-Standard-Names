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
export const ROLE_META = {
  // Emitted by the current dataset builder:
  operator:    { label: 'Operator',    hue: 320, desc: 'Operator applied to a base quantity' },
  axis:        { label: 'Axis',        hue: 200, desc: 'Vector component direction' },
  qualifier:   { label: 'Qualifier',   hue: 35,  desc: 'Qualifier scoping the quantity' },
  aggregation: { label: 'Aggregation', hue: 345, desc: 'Population/species/contribution reduction (total, net)' },
  orbit:       { label: 'Orbit',       hue: 5,   desc: 'Particle orbit / transit class (trapped, co-passing, …)' },
  population:  { label: 'Population',   hue: 25,  desc: 'Species population kind/state (fast, thermal, cold, …)' },
  base:        { label: 'Base',        hue: 260, desc: 'Root quantity from the canonical vocabulary' },
  locus:       { label: 'Locus',       hue: 145, desc: 'Geometric or topological location' },
  process:     { label: 'Process',     hue: 105, desc: 'Mechanism the quantity is due to' },
  unparseable: { label: 'Unparseable', hue: 0,   desc: 'Parser could not decompose this name' },

  // Reserved for future emitter use / hand-authored examples:
  reduction:   { label: 'Reduction',   hue: 65,  desc: 'Aggregation applied to a base quantity' },
  modifier:    { label: 'Modifier',    hue: 35,  desc: 'Qualifier scoping the quantity' },
  subject:     { label: 'Subject',     hue: 15,  desc: 'Entity the quantity applies to' },
  preposition: { label: 'Preposition', hue: 0,   desc: 'Grammatical connector' },
  unknown:     { label: 'Unknown',     hue: 0,   desc: 'Not recognised by the parser vocabulary' },
};

