// Grammar role metadata.
//
// This module has NO parsing logic. The SPA consumes `name.parse[]` from
// the dataset emitter; we only attach human-readable role labels, hue
// values for colour-coding, and one-line descriptions used as default
// notes when a token doesn't carry its own.

export const ROLE_META = {
  reduction:   { label: 'Reduction',   hue: 65,  desc: 'Aggregation applied to a base quantity' },
  modifier:    { label: 'Modifier',    hue: 35,  desc: 'Qualifier scoping the quantity' },
  subject:     { label: 'Subject',     hue: 15,  desc: 'Entity the quantity applies to' },
  axis:        { label: 'Axis',        hue: 200, desc: 'Vector component direction' },
  base:        { label: 'Base',        hue: 260, desc: 'Root quantity from the canonical vocabulary' },
  operator:    { label: 'Operator',    hue: 320, desc: 'Operator-suffix applied to a base' },
  preposition: { label: 'Preposition', hue: 0,   desc: 'Grammatical connector' },
  locus:       { label: 'Locus',       hue: 145, desc: 'Geometric or topological location' },
  unknown:     { label: 'Unknown',     hue: 0,   desc: 'Not recognised by the parser vocabulary' },
};

// Roles whose token can be clicked through to open another catalog entry
// (provided that target name exists in NAMES).
export const CLICKABLE_ROLES = new Set(['base', 'locus', 'subject']);
