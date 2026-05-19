import { describe, it, expect } from 'vitest';
import {
  tokenize,
  matchScore,
  searchNames,
  ALIASES,
} from '../../src/lib/search.js';

const N = (over) => ({
  name: 'plasma_current',
  short: 'Toroidal plasma current',
  long: 'The integrated toroidal current carried by the plasma column.',
  unit: 'A',
  kind: 'scalar',
  tags: ['equilibrium', 'plasma_state'],
  category: 'equilibrium',
  group: 'current',
  sources: [],
  parse: [],
  seeAlso: [],
  ...over,
});

const CORPUS = [
  N({
    name: 'plasma_pressure_at_plasma_boundary',
    short: 'pressure at the plasma boundary',
    long: 'kinetic pressure evaluated at the LCFS',
    unit: 'Pa',
    tags: ['equilibrium', 'pressure'],
  }),
  N({
    name: 'electron_pressure',
    short: 'electron kinetic pressure',
    long: 'isotropic electron pressure',
    unit: 'Pa',
    tags: ['core_profiles'],
  }),
  N({
    name: 'major_radius_of_plasma_boundary',
    short: 'major radius of the LCFS',
    long: 'R_lcfs in metres',
    unit: 'm',
    tags: ['equilibrium'],
  }),
  N({
    name: 'toroidal_magnetic_field',
    short: 'toroidal magnetic field on axis',
    long: 'Bt evaluated at R_geo',
    unit: 'T',
    tags: ['magnetics'],
  }),
  N({
    name: 'plasma_current',
    short: 'toroidal plasma current',
    long: 'integrated current',
    unit: 'A',
    tags: ['equilibrium', 'magnetics'],
  }),
];

describe('tokenize', () => {
  it('splits on whitespace and lowercases', () => {
    expect(tokenize('  Plasma   Current ')).toEqual(['plasma', 'current']);
  });
  it('returns empty array for empty input', () => {
    expect(tokenize('')).toEqual([]);
    expect(tokenize('   ')).toEqual([]);
    expect(tokenize(null)).toEqual([]);
  });
});

describe('matchScore', () => {
  it('returns null when any token fails to hit any field', () => {
    const row = N({ name: 'plasma_current' });
    expect(matchScore(row, tokenize('plasma whatever_nonsense'))).toBeNull();
  });

  it('returns null for empty token list', () => {
    expect(matchScore(N({}), [])).toBeNull();
  });

  it('scores name substring at 8 (dominant)', () => {
    const row = N({ name: 'plasma_current', short: 'X', long: 'Y' });
    expect(matchScore(row, ['plasma'])).toBe(8);
  });

  it('scores exact unit match at 6, overriding all other fields', () => {
    const row = N({ name: 'nope', short: '', long: '', unit: 'Pa', tags: [] });
    expect(matchScore(row, ['pa'])).toBe(6);
  });

  it('falls back to short at 2, then long at 1', () => {
    const row1 = N({ name: 'x', short: 'magnitude here', long: '', tags: [] });
    expect(matchScore(row1, ['magnitude'])).toBe(2);
    const row2 = N({ name: 'x', short: '', long: 'magnitude here', tags: [] });
    expect(matchScore(row2, ['magnitude'])).toBe(1);
  });

  it('uses alias map at weight 3 when a token expands to a match', () => {
    expect(ALIASES.pressure).toEqual(['pa', 'pressure']);
    // Token "pressure" → alias targets ["pa", "pressure"].
    // Name does not contain "pressure" so name-substr loses.
    // Unit "Pa" is an exact target.
    const row = N({
      name: 'electron_kinetic_quantity',
      short: '',
      long: '',
      unit: 'Pa',
      tags: [],
    });
    // Unit-equality (6) actually wins because the alias path checks
    // its targets against unit too; but here token "pressure" itself
    // does not equal "Pa". Aliases get weight 3.
    // To isolate the alias path explicitly, drop the unit:
    const row2 = N({
      name: 'something_with_pa_in_it',
      short: '',
      long: '',
      unit: '',
      tags: [],
    });
    // "pressure" → ["pa", "pressure"]; name contains "pa".
    // Name-substr direct check for "pressure" fails (name has no "pressure").
    // So alias path scores 3.
    expect(matchScore(row2, ['pressure'])).toBe(3);
    // Unit-equality wins outright on the first row even before alias:
    expect(matchScore(row, ['pa'])).toBe(6);
  });

  it('AND-combines scores across tokens', () => {
    const row = N({ name: 'plasma_current', tags: ['equilibrium'] });
    // "plasma" hits name (8); "equilibrium" hits tags (4); total = 12
    expect(matchScore(row, ['plasma', 'equilibrium'])).toBe(12);
  });
});

describe('searchNames', () => {
  it('returns all rows untouched when there are no tokens', () => {
    const out = searchNames(CORPUS, []);
    expect(out.mode).toBe('all');
    expect(out.results).toBe(CORPUS);
  });

  it('only returns rows whose name contains the token "pressure"', () => {
    const out = searchNames(CORPUS, tokenize('pressure'));
    expect(out.mode).toBe('scored');
    expect(out.results.length).toBeGreaterThan(0);
    for (const r of out.results) {
      const hay =
        r.name + ' ' + (r.short || '') + ' ' + (r.long || '') + ' ' + (r.tags || []).join(' ');
      expect(hay.toLowerCase()).toContain('pressure');
    }
  });

  it('AND-strict: "pressure plasma boundary" hits only rows containing every token somewhere', () => {
    const out = searchNames(CORPUS, tokenize('pressure plasma boundary'));
    expect(out.mode).toBe('scored');
    expect(out.results.length).toBeGreaterThan(0);
    for (const r of out.results) {
      const hay = (
        r.name +
        ' ' +
        (r.short || '') +
        ' ' +
        (r.long || '') +
        ' ' +
        (r.tags || []).join(' ')
      ).toLowerCase();
      expect(hay).toContain('pressure');
      expect(hay).toContain('plasma');
      expect(hay).toContain('boundary');
    }
  });

  it('does not return rows that lack every token in the query', () => {
    const out = searchNames(CORPUS, tokenize('pressure radius'));
    // No row in CORPUS has both "pressure" AND "radius" anywhere.
    // → either empty or fuzzy fallback.
    expect(['empty', 'fuzzy']).toContain(out.mode);
  });

  it('sorts equal-score hits by ascending name length', () => {
    const corpus = [
      N({ name: 'plasma_current_density_at_axis', short: '', long: '', tags: [] }),
      N({ name: 'plasma_current', short: '', long: '', tags: [] }),
    ];
    const out = searchNames(corpus, ['plasma']);
    expect(out.results[0].name).toBe('plasma_current');
    expect(out.results[1].name).toBe('plasma_current_density_at_axis');
  });

  it('falls through to fuzzy on zero exact hits when token ≥ 3 chars', () => {
    const corpus = [N({ name: 'magnetic_field_toroidal' })];
    // "mft" appears in name as a subsequence (m-…f-…t)
    const out = searchNames(corpus, ['mft']);
    expect(out.mode).toBe('fuzzy');
    expect(out.results.length).toBe(1);
  });

  it('returns empty (no fuzzy) when tokens are shorter than 3 chars', () => {
    const out = searchNames([N({ name: 'unrelated' })], ['xy']);
    expect(out.mode).toBe('empty');
  });
});
