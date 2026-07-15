import { describe, it, expect, beforeEach } from 'vitest';
import { parseHash, writeHash } from '../../src/lib/url-state.js';

describe('parseHash', () => {
  it('reads a shareable standard-term detail', () => {
    location.hash = '#/grammar?term=last_closed_flux_surface';
    expect(parseHash()).toEqual({
      view: 'grammar', name: null, query: '', term: 'last_closed_flux_surface',
    });
  });
  beforeEach(() => {
    history.replaceState(null, '', '/');
  });

  it('defaults to browse view, no name, empty query', () => {
    expect(parseHash()).toEqual({ view: 'browse', name: null, query: '' });
  });

  it('reads matrix view from the first path segment', () => {
    location.hash = '#/matrix';
    expect(parseHash().view).toBe('matrix');
  });

  it('coerces legacy #/map to browse', () => {
    location.hash = '#/map';
    expect(parseHash().view).toBe('browse');
  });

  it('coerces unknown views to browse', () => {
    location.hash = '#/unknown';
    expect(parseHash().view).toBe('browse');
  });

  it('reads name from the second path segment, decoding percent escapes', () => {
    location.hash = '#/browse/foo_bar';
    expect(parseHash()).toEqual({ view: 'browse', name: 'foo_bar', query: '' });
    location.hash = '#/browse/foo%20bar';
    expect(parseHash().name).toBe('foo bar');
  });

  it('reads query from ?q=', () => {
    location.hash = '#/browse?q=safety+factor';
    expect(parseHash()).toEqual({
      view: 'browse',
      name: null,
      query: 'safety factor',
    });
  });

  it('reads view + name + query together', () => {
    location.hash = '#/browse/safety_factor?q=safety';
    expect(parseHash()).toEqual({
      view: 'browse',
      name: 'safety_factor',
      query: 'safety',
    });
  });
});

describe('writeHash', () => {
  beforeEach(() => {
    history.replaceState(null, '', '/');
  });

  it('writes view-only path for matrix', () => {
    writeHash({ view: 'matrix', name: null, query: '' });
    expect(location.hash).toBe('#/matrix');
  });

  it('writes view + name', () => {
    writeHash({ view: 'browse', name: 'safety_factor', query: '' });
    expect(location.hash).toBe('#/browse/safety_factor');
  });

  it('writes view + name + query, encoding special characters', () => {
    writeHash({ view: 'browse', name: 'safety_factor', query: 'safety factor' });
    expect(location.hash).toBe('#/browse/safety_factor?q=safety%20factor');
  });

  it('does not push history when hash is unchanged', () => {
    history.replaceState(null, '', '#/browse/foo');
    const before = history.length;
    writeHash({ view: 'browse', name: 'foo', query: '' });
    expect(history.length).toBe(before);
  });
});

describe('round-trip', () => {
  beforeEach(() => {
    history.replaceState(null, '', '/');
  });

  for (const s of [
    { view: 'browse', name: null, query: '' },
    { view: 'matrix', name: null, query: '' },
    { view: 'browse', name: 'safety_factor', query: '' },
    { view: 'browse', name: 'poloidal_magnetic_field', query: 'magnetic' },
    { view: 'browse', name: 'a:b#c', query: 'q with spaces' },
  ]) {
    it(`round-trips ${JSON.stringify(s)}`, () => {
      writeHash(s);
      expect(parseHash()).toEqual(s);
    });
  }
});
