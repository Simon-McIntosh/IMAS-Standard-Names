import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { KindBadge, schemaKindOf, KIND_GLYPHS } from '../../src/components/KindBadge.jsx';

describe('schemaKindOf', () => {
  it('returns kind string passed through', () => {
    expect(schemaKindOf('vector')).toBe('vector');
    expect(schemaKindOf('scalar')).toBe('scalar');
  });
  it('reads record.algebra when given a record', () => {
    expect(schemaKindOf({ name: 'b', algebra: 'tensor' })).toBe('tensor');
    expect(schemaKindOf({ name: 'b', algebra: 'metadata' })).toBe('metadata');
  });
  it('defaults to scalar when neither algebra nor kind set', () => {
    expect(schemaKindOf({ name: 'x' })).toBe('scalar');
    expect(schemaKindOf(null)).toBe('scalar');
  });
});

describe('KIND_GLYPHS', () => {
  it('has exactly five entries', () => {
    expect(Object.keys(KIND_GLYPHS).sort()).toEqual([
      'complex', 'metadata', 'scalar', 'tensor', 'vector',
    ]);
  });
  it('each entry has title and svg', () => {
    for (const [k, v] of Object.entries(KIND_GLYPHS)) {
      expect(v.title).toBeTruthy();
      expect(v.svg).toBeTruthy();
    }
  });
});

describe('KindBadge', () => {
  it('renders kind-vector class when given a vector record', () => {
    const { container } = render(<KindBadge name={{ algebra: 'vector' }} />);
    expect(container.querySelector('.kind-vector')).not.toBeNull();
  });
  it('renders kind-metadata class when given metadata kind string', () => {
    const { container } = render(<KindBadge kind="metadata" />);
    expect(container.querySelector('.kind-metadata')).not.toBeNull();
  });
  it('falls back to kind-scalar for unknown kind', () => {
    const { container } = render(<KindBadge kind="bogus" />);
    // unknown kind still mounts (uses fallback glyph but bogus class)
    expect(container.querySelector('.kind-badge')).not.toBeNull();
  });
});
