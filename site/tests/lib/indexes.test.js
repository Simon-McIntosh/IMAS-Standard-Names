import { describe, it, expect } from 'vitest';
import { clusterKey, clusterDescriptor, groupSources } from '../../src/lib/indexes.js';

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
