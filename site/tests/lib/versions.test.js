import { describe, expect, it } from 'vitest';
import { parseVersion, sortVersions } from '../../src/lib/versions.js';

describe('parseVersion', () => {
  it('parses a stable release with no rc suffix', () => {
    expect(parseVersion('v0.2.0')).toEqual({ major: 0, minor: 2, patch: 0, rc: null });
  });

  it('parses a release candidate', () => {
    expect(parseVersion('v0.2.0rc64')).toEqual({ major: 0, minor: 2, patch: 0, rc: 64 });
  });

  it('returns null for an unparseable string', () => {
    expect(parseVersion('main')).toBeNull();
    expect(parseVersion('')).toBeNull();
    expect(parseVersion(undefined)).toBeNull();
  });
});

describe('sortVersions', () => {
  it('fixes the exact observed mis-ordering: rc64 > rc63 > ... > rc9 > rc8 > rc7 > rc6', () => {
    const input = [
      { version: 'v0.2.0rc64' },
      { version: 'v0.2.0rc9' },
      { version: 'v0.2.0rc8' },
      { version: 'v0.2.0rc7' },
      { version: 'v0.2.0rc63' },
      { version: 'v0.2.0rc62' },
      { version: 'v0.2.0rc61' },
      { version: 'v0.2.0rc60' },
      { version: 'v0.2.0rc6' },
    ];
    const sorted = sortVersions(input).map((v) => v.version);
    expect(sorted).toEqual([
      'v0.2.0rc64',
      'v0.2.0rc63',
      'v0.2.0rc62',
      'v0.2.0rc61',
      'v0.2.0rc60',
      'v0.2.0rc9',
      'v0.2.0rc8',
      'v0.2.0rc7',
      'v0.2.0rc6',
    ]);
  });

  it('sorts a stable release above all of its own release candidates', () => {
    const input = [
      { version: 'v0.2.0rc64' },
      { version: 'v0.2.0' },
      { version: 'v0.2.0rc1' },
    ];
    expect(sortVersions(input).map((v) => v.version)).toEqual([
      'v0.2.0',
      'v0.2.0rc64',
      'v0.2.0rc1',
    ]);
  });

  it('orders across major/minor/patch numerically before considering rc', () => {
    const input = [
      { version: 'v0.2.0rc5' },
      { version: 'v1.0.0' },
      { version: 'v0.10.0' },
      { version: 'v0.2.9' },
      { version: 'v0.2.10' },
    ];
    expect(sortVersions(input).map((v) => v.version)).toEqual([
      'v1.0.0',
      'v0.10.0',
      'v0.2.10',
      'v0.2.9',
      'v0.2.0rc5',
    ]);
  });

  it('sorts unparseable entries last, preserving their original relative order', () => {
    const input = [
      { version: 'v0.2.0rc1' },
      { version: 'main' },
      { version: 'v0.1.0' },
      { version: 'latest' },
      { version: 'dev-branch' },
    ];
    expect(sortVersions(input).map((v) => v.version)).toEqual([
      'v0.2.0rc1',
      'v0.1.0',
      'main',
      'latest',
      'dev-branch',
    ]);
  });

  it('accepts a bare string list', () => {
    expect(sortVersions(['v0.2.0rc1', 'v0.2.0rc10', 'v0.2.0'])).toEqual([
      'v0.2.0',
      'v0.2.0rc10',
      'v0.2.0rc1',
    ]);
  });

  it('handles duplicate versions without dropping entries', () => {
    const input = [{ version: 'v0.2.0rc1' }, { version: 'v0.2.0rc1' }];
    expect(sortVersions(input)).toHaveLength(2);
  });

  it('returns an empty array for null, undefined, or non-array input', () => {
    expect(sortVersions(null)).toEqual([]);
    expect(sortVersions(undefined)).toEqual([]);
    expect(sortVersions('not-an-array')).toEqual([]);
  });

  it('returns an empty array for an empty list', () => {
    expect(sortVersions([])).toEqual([]);
  });

  it('does not mutate the input array', () => {
    const input = [{ version: 'v0.2.0rc1' }, { version: 'v0.2.0rc64' }];
    const snapshot = [...input];
    sortVersions(input);
    expect(input).toEqual(snapshot);
    expect(input[0]).toBe(snapshot[0]);
    expect(input[1]).toBe(snapshot[1]);
  });
});
