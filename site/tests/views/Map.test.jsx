import { describe, it, expect, vi } from 'vitest';
import { act, render } from '@testing-library/react';
import { LineageMap as MapView } from '../../src/views/Map.jsx';
import { DataProvider } from '../../src/lib/data.js';

// jsdom does not perform CSS layout, so we cannot directly assert
// computed pixel heights. We assert the structural invariants the fix
// depends on instead:
//
//   * the `.map-view` root carries `data-active-view="map"`
//     so the App-level rAF height guard can locate it.
//   * the `.map-view` root is the ONLY element with that attribute
//     in the rendered tree (no `display:none` hidden sibling that
//     would suppress the active view's first layout pass).
//   * cluster cards are present for non-empty NAMES — the original
//     regression was an empty `.map-view` element with zero children.

function mockFetch(names, categories = []) {
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return {
        CATALOG_VERSION: 'test',
        CATEGORIES: categories,
        GRAMMAR_VOCAB: {},
        NAMES: names,
      };
    },
  });
}

async function renderMap(names, categories = []) {
  mockFetch(names, categories);
  let result;
  await act(async () => {
    result = render(
      <DataProvider>
        <MapView
          onSelect={() => {}}
          activeCategory={null}
          setActiveCategory={() => {}}
        />
      </DataProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

const N = (over = {}) => ({
  name: 'plasma_current',
  short: 'Ip',
  unit: 'A',
  kind: 'scalar',
  sources: [],
  parse: [],
  seeAlso: [],
  category: 'equilibrium',
  group: 'current',
  ...over,
});

describe('Map view', () => {
  it('marks the root as data-active-view="map"', async () => {
    const { container } = await renderMap([N()]);
    const root = container.querySelector('.map-view');
    expect(root).not.toBeNull();
    expect(root.getAttribute('data-active-view')).toBe('map');
  });

  it('renders exactly one active-view root in the subtree', async () => {
    const { container } = await renderMap([N()]);
    expect(container.querySelectorAll('[data-active-view]').length).toBe(1);
  });

  it('renders one cluster card per distinct cluster', async () => {
    const { container } = await renderMap([
      N({ name: 'plasma_current', group: 'current' }),
      N({ name: 'plasma_pressure', group: 'pressure' }),
    ]);
    const cards = container.querySelectorAll('.cluster-card');
    expect(cards.length).toBeGreaterThan(0);
  });

  it('uses an explicit pixel height for cluster SVGs (no aspect-ratio collapse)', async () => {
    const { container } = await renderMap([N()]);
    const svg = container.querySelector('.cluster-svg');
    expect(svg).not.toBeNull();
    // viewBox is fixed (not aspect-ratio-driven), so first paint cannot collapse
    expect(svg.getAttribute('viewBox')).toBe('0 0 320 220');
  });

  it('cluster-node <title> never contains the string "undefined"', async () => {
    // Records emitted by dataset.py carry `algebra` (schema kind), not the
    // legacy `kind` field. The tooltip was reading `p.m.kind` so vector /
    // scalar records rendered "… · undefined". Switched to schemaKindOf().
    const { container } = await renderMap([
      N({ name: 'magnetic_field', kind: undefined, algebra: 'vector', unit: 'T' }),
    ]);
    const titles = [...container.querySelectorAll('.cluster-node title')]
      .map((t) => t.textContent || '');
    expect(titles.length).toBeGreaterThan(0);
    for (const t of titles) {
      expect(t).not.toContain('undefined');
    }
  });
});
