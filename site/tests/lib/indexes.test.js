import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import {
  clusterKey,
  clusterDescriptor,
  groupSources,
  useGroupIndex,
  useChildIndex,
} from '../../src/lib/indexes.js';

const NAMES = [
  {
    name: 'safety_factor_at_magnetic_axis',
    category: 'equilibrium',
    group: 'magnetic axis',
    parent: 'safety_factor',
    kind: 'at_point',
    locus: 'magnetic_axis',
    sources: [],
  },
  {
    name: 'major_radius_of_magnetic_axis',
    category: 'equilibrium',
    group: 'magnetic axis',
    parent: 'major_radius',
    kind: 'at_point',
    locus: 'magnetic_axis',
    sources: [],
  },
  {
    name: 'poloidal_magnetic_field',
    category: 'equilibrium',
    group: 'magnetic field',
    parent: 'magnetic_field',
    kind: 'component',
    axis: 'poloidal',
    sources: [],
  },
  {
    name: 'toroidal_magnetic_field',
    category: 'equilibrium',
    group: 'magnetic field',
    parent: 'magnetic_field',
    kind: 'component',
    axis: 'toroidal',
    sources: [],
  },
  {
    name: 'magnetic_field',
    category: 'equilibrium',
    group: 'magnetic field',
    parent: null,
    kind: 'base',
    sources: [],
  },
];

describe('clusterKey', () => {
  it('combines category and group with "::"', () => {
    expect(clusterKey({ category: 'foo', group: 'bar' })).toBe('foo::bar');
  });
});

describe('clusterDescriptor', () => {
  it('returns locus root for an at_point-dominated cluster', () => {
    const desc = clusterDescriptor(
      NAMES.filter((n) => n.group === 'magnetic axis'),
      NAMES,
    );
    expect(desc).toEqual({ root: 'magnetic_axis', kind: 'locus', real: false });
  });

  it('returns base root for a component cluster', () => {
    const desc = clusterDescriptor(
      NAMES.filter((n) => n.group === 'magnetic field' && n.kind === 'component'),
      NAMES,
    );
    expect(desc).toEqual({ root: 'magnetic_field', kind: 'base', real: true });
  });

  it('marks the root as real if it exists in NAMES', () => {
    const members = NAMES.filter((n) => n.group === 'magnetic field' && n.kind === 'component');
    expect(clusterDescriptor(members, NAMES).real).toBe(true);
  });

  it('falls back to concept descriptor when neither rule fires', () => {
    const desc = clusterDescriptor(
      [{ name: 'x', kind: 'base', group: 'mixed', parent: null }],
      NAMES,
    );
    expect(desc.kind).toBe('concept');
    expect(desc.real).toBe(false);
  });
});

describe('useGroupIndex', () => {
  it('sorts cluster members by cmpOrderKey (tier order, not alpha)', () => {
    // magnetic_field family: vector base (tier 0) before components
    // (tier 1, ordered by axis index) before magnitude (tier 2).
    const family = [
      { name: 'poloidal_magnetic_field',  algebra: 'vector', sort_tier: 1, sort_axis_index: 3, category: 'magnetic', group: 'mf' },
      { name: 'magnetic_field',           algebra: 'vector', sort_tier: 0, sort_axis_index: 99, category: 'magnetic', group: 'mf' },
      { name: 'magnetic_field_magnitude', algebra: 'scalar', sort_tier: 2, sort_axis_index: 99, category: 'magnetic', group: 'mf' },
      { name: 'radial_magnetic_field',    algebra: 'vector', sort_tier: 1, sort_axis_index: 0, category: 'magnetic', group: 'mf' },
    ];
    const { result } = renderHook(() => useGroupIndex(family));
    const ordered = result.current['magnetic::mf'].map((n) => n.name);
    expect(ordered).toEqual([
      'magnetic_field',
      'radial_magnetic_field',
      'poloidal_magnetic_field',
      'magnetic_field_magnitude',
    ]);
  });
});

describe('useChildIndex', () => {
  it('sorts children by cmpOrderKey', () => {
    const all = [
      { name: 'B', parent: 'P', sort_tier: 1, sort_axis_index: 2 },
      { name: 'A', parent: 'P', sort_tier: 1, sort_axis_index: 0 },
      { name: 'C', parent: 'P', sort_tier: 1, sort_axis_index: 1 },
    ];
    const { result } = renderHook(() => useChildIndex(all));
    expect(result.current['P'].map((n) => n.name)).toEqual(['A', 'C', 'B']);
  });
});

describe('groupSources', () => {
  it('groups by first path segment', () => {
    const sources = [
      { path: 'equilibrium/a/b', status: 'composed' },
      { path: 'equilibrium/c', status: 'composed' },
      { path: 'magnetics/ip/data', status: 'composed' },
    ];
    const groups = groupSources(sources);
    expect(groups).toHaveLength(2);
    expect(groups[0][0]).toBe('equilibrium');
    expect(groups[0][1]).toHaveLength(2);
    expect(groups[1][0]).toBe('magnetics');
  });

  it('sorts groups descending by member count', () => {
    const sources = [
      { path: 'magnetics/a', status: 'composed' },
      { path: 'equilibrium/a', status: 'composed' },
      { path: 'equilibrium/b', status: 'composed' },
      { path: 'equilibrium/c', status: 'composed' },
    ];
    const groups = groupSources(sources);
    expect(groups[0][0]).toBe('equilibrium');
    expect(groups[1][0]).toBe('magnetics');
  });
});
