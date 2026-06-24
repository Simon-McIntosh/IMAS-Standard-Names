import { describe, it, expect } from 'vitest';
import {
  composeName,
  matchesComposition,
  qualifierKind,
  seedFromParse,
} from '../../src/lib/grammar-compose.js';

// Minimal but faithful vocab — only the fields the compose/seed logic reads.
const VOCAB = {
  operators: [
    { token: 'magnitude', kind: 'unary_postfix' },
    { token: 'gradient', kind: 'unary_prefix' },
    { token: 'ratio', kind: 'binary' },
  ],
  components: [{ token: 'poloidal' }, { token: 'radial' }],
  physical_bases: [
    { token: 'magnetic_field' },
    { token: 'power' },
    { token: 'temperature' },
    { token: 'radius' },
    { token: 'safety_factor' },
  ],
  geometry_carriers: [{ token: 'centroid' }],
  locus_registry: [
    { token: 'magnetic_axis', type: 'position', relations: ['at', 'of'] },
    { token: 'flux_loop', type: 'entity', relations: ['of'] },
  ],
  regions: [{ token: 'core_region' }],
  aggregations: [{ token: 'total' }],
  orbits: [{ token: 'trapped' }],
  populations: [{ token: 'fast' }],
  subjects: [{ token: 'electron' }, { token: 'ion' }],
  qualifiers: [
    { token: 'total' },
    { token: 'external' },
    { token: 'heating' },
    { token: 'major' },
    { token: 'electron' },
    { token: 'ion' },
    { token: 'fast' },
    { token: 'trapped' },
  ],
};

// Each case: a real ISN name and its authoritative emitted parse segments.
const CASES = [
  ['total_external_heating_power', [
    { role: 'aggregation', text: 'total' },
    { role: 'qualifier', text: 'external' },
    { role: 'qualifier', text: 'heating' },
    { role: 'base', text: 'power' },
  ]],
  ['major_radius_of_flux_loop', [
    { role: 'qualifier', text: 'major' },
    { role: 'base', text: 'radius' },
    { role: 'locus', text: 'of_flux_loop' },
  ]],
  ['poloidal_magnetic_field', [
    { role: 'axis', text: 'poloidal' },
    { role: 'base', text: 'magnetic_field' },
  ]],
  ['safety_factor_at_magnetic_axis', [
    { role: 'base', text: 'safety_factor' },
    { role: 'locus', text: 'at_magnetic_axis' },
  ]],
  ['magnetic_field_magnitude', [
    { role: 'base', text: 'magnetic_field' },
    { role: 'operator', text: 'magnitude' },
  ]],
  ['electron_temperature', [
    { role: 'subject', text: 'electron' },
    { role: 'base', text: 'temperature' },
  ]],
];

describe('grammar-compose round-trip', () => {
  it.each(CASES)('reconstructs %s from its parse', (name, parse) => {
    const state = seedFromParse(parse, VOCAB, name);
    expect(composeName(state)).toBe(name);
    expect(state.raw).toBeNull(); // genuinely decomposed, not a verbatim fallback
  });

  it('decomposes total_external_heating_power into ordered qualifiers (the reported bug)', () => {
    const state = seedFromParse(CASES[0][1], VOCAB, 'total_external_heating_power');
    expect(state.qualifiers).toEqual(['total', 'external', 'heating']);
    expect(state.base.token).toBe('power');
    expect(state.mechanism).toBeNull(); // 'heating' must NOT become a due_to process
  });

  it('keeps the major qualifier on major_radius_of_flux_loop (the reported bug)', () => {
    const state = seedFromParse(CASES[1][1], VOCAB, 'major_radius_of_flux_loop');
    expect(state.qualifiers).toEqual(['major']);
    expect(state.base.token).toBe('radius');
    expect(state.locus).toEqual({ relation: 'of', token: 'flux_loop' });
  });

  it('falls back to the verbatim name when the parse is lossy (binary operator)', () => {
    // The emitter collapses binary operands to a `placeholder` base, so the
    // name cannot be reconstructed from the flat parse — never fabricate.
    const name = 'ratio_of_argon_density_to_electron_density';
    const parse = [
      { role: 'operator', text: 'ratio' },
      { role: 'base', text: 'placeholder' },
    ];
    const state = seedFromParse(parse, VOCAB, name);
    expect(state.raw).toBe(name);
    expect(composeName(state)).toBe(name);
  });

  it('classifies qualifier sub-kinds for colour-coding', () => {
    expect(qualifierKind('total', VOCAB)).toBe('aggregation');
    expect(qualifierKind('trapped', VOCAB)).toBe('orbit');
    expect(qualifierKind('fast', VOCAB)).toBe('population');
    expect(qualifierKind('electron', VOCAB)).toBe('subject');
    expect(qualifierKind('external', VOCAB)).toBe('qualifier');
  });
});

describe('matchesComposition', () => {
  const ns = (name, parse) => seedFromParse(parse, VOCAB, name);
  const poloidal = ns('poloidal_magnetic_field', CASES[2][1]);
  const bareField = ns('magnetic_field', [{ role: 'base', text: 'magnetic_field' }]);

  it('matches every name when the builder is empty', () => {
    const empty = seedFromParse([], VOCAB);
    expect(matchesComposition(poloidal, empty)).toBe(true);
    expect(matchesComposition(bareField, empty)).toBe(true);
  });

  it('filters by base across the family', () => {
    const builder = { qualifiers: [], base: { token: 'magnetic_field' } };
    expect(matchesComposition(poloidal, builder)).toBe(true);
    expect(matchesComposition(bareField, builder)).toBe(true);
  });

  it('filters by projection axis', () => {
    const builder = { qualifiers: [], axis: 'poloidal' };
    expect(matchesComposition(poloidal, builder)).toBe(true);
    expect(matchesComposition(bareField, builder)).toBe(false);
  });

  it('filters by every qualifier in the ordered list', () => {
    const total = ns('total_external_heating_power', CASES[0][1]);
    expect(matchesComposition(total, { qualifiers: ['external', 'heating'] })).toBe(true);
    expect(matchesComposition(total, { qualifiers: ['external', 'absent'] })).toBe(false);
  });
});
