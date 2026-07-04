import { describe, expect, it } from 'vitest';
import { FILTERABLE_PARSE_ROLES, ROLE_META } from '../../src/lib/grammar.js';

// The exact set of `role` values the Python dataset emitter produces —
// see imas_standard_names/catalog/dataset.py::_derive_grammar_facets.
// Hardcoded ONCE here so any future emitter change that isn't mirrored into
// grammar.js's `filterable` flags fails this test instead of silently
// giving a role chips with no '+' or a filter that never applies.
const EMITTED_ROLES = [
  'base',
  'operator',
  'axis',
  'locus',
  'subject',
  'process',
  'qualifier',
  'aggregation',
  'orbit',
  'population',
  'zone',
  'channel',
  'channel_qualifier',
  'unparseable',
];

// Every emitted role except `unparseable` should be filterable — a filter on
// "couldn't parse" is not a useful facet.
const EMITTED_FILTERABLE = EMITTED_ROLES.filter((r) => r !== 'unparseable');

describe('FILTERABLE_PARSE_ROLES tracks the dataset emitter', () => {
  it('every emitted role resolves to a non-Unknown label in ROLE_META', () => {
    for (const role of EMITTED_ROLES) {
      expect(ROLE_META[role], `emitter role "${role}" missing from ROLE_META`).toBeDefined();
      expect(ROLE_META[role].label).not.toBe('Unknown');
    }
  });

  it('contains every emitted filterable role', () => {
    for (const role of EMITTED_FILTERABLE) {
      expect(FILTERABLE_PARSE_ROLES, `emitter role "${role}" is not filterable`).toContain(role);
    }
  });

  it('never marks unparseable filterable', () => {
    expect(FILTERABLE_PARSE_ROLES).not.toContain('unparseable');
  });

  it('is exactly the emitted filterable set — no extra reserved roles leak in', () => {
    // Sorted compare so an added-but-unemitted `filterable: true` (e.g. on the
    // reserved reduction/modifier entries) trips the test too.
    expect([...FILTERABLE_PARSE_ROLES].sort()).toEqual([...EMITTED_FILTERABLE].sort());
  });
});
