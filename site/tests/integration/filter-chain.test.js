import { describe, expect, it } from 'vitest';
import { FILTERABLE_PARSE_ROLES } from '../../src/lib/grammar.js';

// Re-implementation of the parse-driven filter chain that App.jsx applies.
// The parse-role keys come from the shared FILTERABLE_PARSE_ROLES (same
// source App consumes) so this test tracks the real filter set instead of a
// third hand-copy that drifted from the emitter.
const PARSE_FILTER_KEYS = FILTERABLE_PARSE_ROLES;

function passesFilters(n, filters) {
  if (filters.category?.size && !filters.category.has(n.category)) return false;
  if (filters.kind?.size && !filters.kind.has(n.algebra || 'scalar')) return false;
  if (filters.lifecycle?.size && !filters.lifecycle.has(n.status || 'active')) return false;
  if (filters.unit?.size && !filters.unit.has(n.unit)) return false;

  const anyParse = PARSE_FILTER_KEYS.some((k) => filters[k]?.size > 0);
  if (anyParse) {
    const parse = n.parse || [];
    for (const k of PARSE_FILTER_KEYS) {
      if (!filters[k]?.size) continue;
      const matchesAll = [...filters[k]].every((text) =>
        parse.some((tok) => tok.role === k && tok.text === text) || n[k] === text,
      );
      if (!matchesAll) return false;
    }
  }
  return true;
}

function f(overrides) {
  const base = { category: new Set(), kind: new Set(), lifecycle: new Set(), unit: new Set() };
  for (const k of PARSE_FILTER_KEYS) base[k] = new Set();
  return { ...base, ...overrides };
}

describe('parse-driven filter chain', () => {
  it('passes when no filters active', () => {
    const n = { name: 'foo', parse: [] };
    expect(passesFilters(n, f({}))).toBe(true);
  });

  it('passes when parse contains a matching (role, text)', () => {
    const n = {
      name: 'safety_factor_at_magnetic_axis',
      parse: [
        { role: 'base', text: 'safety_factor' },
        { role: 'preposition', text: 'at' },
        { role: 'locus', text: 'magnetic_axis' },
      ],
    };
    expect(passesFilters(n, f({ locus: new Set(['magnetic_axis']) }))).toBe(true);
  });

  it('fails when parse lacks the (role, text)', () => {
    const n = {
      name: 'safety_factor_at_magnetic_axis',
      parse: [{ role: 'base', text: 'safety_factor' }, { role: 'locus', text: 'magnetic_axis' }],
    };
    expect(passesFilters(n, f({ locus: new Set(['plasma_boundary']) }))).toBe(false);
  });

  it('axis=vertical KEEPS vertical_coordinate_of_x_point (parse has axis token vertical)', () => {
    const n = {
      name: 'vertical_coordinate_of_x_point',
      parse: [
        { role: 'axis', text: 'vertical' },
        { role: 'base', text: 'coordinate' },
        { role: 'preposition', text: 'of' },
        { role: 'locus', text: 'x_point' },
      ],
    };
    expect(passesFilters(n, f({ axis: new Set(['vertical']) }))).toBe(true);
  });

  it('axis=vertical drops a name whose parse has no vertical axis token', () => {
    const n = {
      name: 'plasma_current',
      parse: [{ role: 'base', text: 'current' }, { role: 'subject', text: 'plasma' }],
    };
    expect(passesFilters(n, f({ axis: new Set(['vertical']) }))).toBe(false);
  });

  it('multi-key parse filters AND across roles', () => {
    const n = {
      name: 'electron_temperature_at_plasma_boundary',
      parse: [
        { role: 'subject', text: 'electron' },
        { role: 'base', text: 'temperature' },
        { role: 'preposition', text: 'at' },
        { role: 'locus', text: 'plasma_boundary' },
      ],
    };
    expect(passesFilters(n, f({
      subject: new Set(['electron']),
      locus:   new Set(['plasma_boundary']),
    }))).toBe(true);
    expect(passesFilters(n, f({
      subject: new Set(['electron']),
      locus:   new Set(['magnetic_axis']),
    }))).toBe(false);
  });

  it('qualifier filter keeps a name with that qualifier token, drops one without', () => {
    const kept = {
      name: 'toroidal_plasma_current',
      parse: [
        { role: 'qualifier', text: 'toroidal' },
        { role: 'subject', text: 'plasma' },
        { role: 'base', text: 'current' },
      ],
    };
    const dropped = {
      name: 'plasma_current',
      parse: [{ role: 'subject', text: 'plasma' }, { role: 'base', text: 'current' }],
    };
    expect(passesFilters(kept, f({ qualifier: new Set(['toroidal']) }))).toBe(true);
    expect(passesFilters(dropped, f({ qualifier: new Set(['toroidal']) }))).toBe(false);
  });

  it('aggregation filter actually filters (was a silent no-op before)', () => {
    const total = {
      name: 'total_radiated_power',
      parse: [
        { role: 'aggregation', text: 'total' },
        { role: 'base', text: 'radiated_power' },
      ],
    };
    const partial = {
      name: 'radiated_power',
      parse: [{ role: 'base', text: 'radiated_power' }],
    };
    expect(passesFilters(total, f({ aggregation: new Set(['total']) }))).toBe(true);
    expect(passesFilters(partial, f({ aggregation: new Set(['total']) }))).toBe(false);
  });

  it('non-parse filters still apply (unit)', () => {
    const n = { name: 'temperature', unit: 'eV', parse: [{ role: 'base', text: 'temperature' }] };
    expect(passesFilters(n, f({ unit: new Set(['eV']) }))).toBe(true);
    expect(passesFilters(n, f({ unit: new Set(['m']) }))).toBe(false);
  });
});
