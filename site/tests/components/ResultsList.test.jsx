import { describe, it, expect } from 'vitest';
import { act, render, fireEvent } from '@testing-library/react';
import { ResultsList } from '../../src/components/ResultsList.jsx';
import { DataProvider } from '../../src/lib/data.js';

const MAGNETIC_FAMILY = [
  { name: 'magnetic_field',           algebra: 'vector', sort_tier: 0, sort_axis_index: 99, category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T' },
  { name: 'radial_magnetic_field',    algebra: 'vector', sort_tier: 1, sort_axis_index: 0,  category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T', axis: 'radial' },
  { name: 'toroidal_magnetic_field',  algebra: 'vector', sort_tier: 1, sort_axis_index: 1,  category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T', axis: 'toroidal' },
  { name: 'vertical_magnetic_field',  algebra: 'vector', sort_tier: 1, sort_axis_index: 2,  category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T', axis: 'vertical' },
  { name: 'poloidal_magnetic_field',  algebra: 'vector', sort_tier: 1, sort_axis_index: 3,  category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T', axis: 'poloidal' },
  { name: 'magnetic_field_magnitude', algebra: 'scalar', sort_tier: 2, sort_axis_index: 99, category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T' },
  { name: 'flux_surface_averaged_magnetic_field', algebra: 'scalar', sort_tier: 3, sort_axis_index: 99, category: 'magnetic', group: 'magnetic field', short: '', sources: [], unit: 'T' },
];

// Why this test exists:
//   The first ship of the new weighted-AND search produced correct
//   per-row scores but the UI buried them under cluster grouping —
//   each group's items were re-sorted alphabetically, so typing
//   "pressure" pushed `area_of_flux_surface` (score 1, long-only
//   match) to the top of the Equilibrium cluster while
//   `*_pressure` rows (score 8, name match) sat further down.
//
//   This test pins the invariant: when `searchMode === 'scored'`,
//   the rendered DOM order MUST match the order in `results`,
//   regardless of `groupBy`.

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

async function renderList({ results, groupBy, searchMode, query, searchTokens, dense = 'comfortable' }) {
  mockFetch(results, [
    { id: 'equilibrium', label: 'Equilibrium', count: 0 },
    { id: 'transport', label: 'Transport', count: 0 },
  ]);
  let result;
  await act(async () => {
    result = render(
      <DataProvider>
        <ResultsList
          results={results}
          selected={null}
          onSelect={() => {}}
          dense={dense}
          groupBy={groupBy}
          setGroupBy={() => {}}
          query={query}
          searchTokens={searchTokens}
          searchMode={searchMode}
        />
      </DataProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

const ROW = (over) => ({
  name: 'x',
  short: '',
  unit: '',
  algebra: 'scalar',
  sources: [],
  parse: [],
  seeAlso: [],
  category: 'equilibrium',
  group: 'g1',
  ...over,
});

function renderedNamesInOrder(container) {
  return [...container.querySelectorAll('.result-name')].map((el) => el.textContent);
}

describe('ResultsList score ordering', () => {
  it('preserves score order in flat mode (groupBy=none)', async () => {
    const results = [
      ROW({ name: 'ion_pressure' }),
      ROW({ name: 'electron_pressure' }),
      ROW({ name: 'area_of_flux_surface' }),
    ];
    const { container } = await renderList({
      results,
      groupBy: 'none',
      searchMode: 'scored',
      query: 'pressure',
      searchTokens: ['pressure'],
    });
    expect(renderedNamesInOrder(container)).toEqual([
      'ion_pressure',
      'electron_pressure',
      'area_of_flux_surface',
    ]);
  });

  it('ignores cluster grouping when searchMode is scored (regression: rc7 pressure→major_radius)', async () => {
    // Same names, default groupBy='cluster'. Without the score-mode
    // override, cluster grouping would re-sort each group's items
    // alphabetically and `area_of_flux_surface` would jump to the top.
    const results = [
      ROW({ name: 'ion_pressure', category: 'transport', group: 'pressure' }),
      ROW({ name: 'electron_pressure', category: 'transport', group: 'pressure' }),
      ROW({ name: 'area_of_flux_surface', category: 'equilibrium', group: 'flux' }),
    ];
    const { container } = await renderList({
      results,
      groupBy: 'cluster',
      searchMode: 'scored',
      query: 'pressure',
      searchTokens: ['pressure'],
    });
    expect(renderedNamesInOrder(container)).toEqual([
      'ion_pressure',
      'electron_pressure',
      'area_of_flux_surface',
    ]);
  });

  it('ignores category grouping when searchMode is scored', async () => {
    const results = [
      ROW({ name: 'ion_pressure', category: 'transport' }),
      ROW({ name: 'electron_pressure', category: 'transport' }),
      ROW({ name: 'area_of_flux_surface', category: 'equilibrium' }),
    ];
    const { container } = await renderList({
      results,
      groupBy: 'category',
      searchMode: 'scored',
      query: 'pressure',
      searchTokens: ['pressure'],
    });
    expect(renderedNamesInOrder(container)).toEqual([
      'ion_pressure',
      'electron_pressure',
      'area_of_flux_surface',
    ]);
  });

  it('shows the "sorted by relevance" badge in scored mode', async () => {
    const { container } = await renderList({
      results: [ROW({ name: 'ion_pressure' })],
      groupBy: 'cluster',
      searchMode: 'scored',
      query: 'pressure',
      searchTokens: ['pressure'],
    });
    expect(container.querySelector('.results-sort-by')).not.toBeNull();
  });

  it('respects cluster grouping when no search is active', async () => {
    const results = [
      ROW({ name: 'ion_pressure', category: 'transport', group: 'pressure' }),
      ROW({ name: 'area_of_flux_surface', category: 'equilibrium', group: 'flux' }),
    ];
    const { container } = await renderList({
      results,
      groupBy: 'cluster',
      searchMode: 'all',
      query: '',
      searchTokens: [],
    });
    // Equilibrium cluster comes before Transport alphabetically; both
    // groups present.
    expect(container.querySelectorAll('.result-group-head').length).toBe(2);
    expect(container.querySelector('.results-sort-by')).toBeNull();
  });
});

describe('ResultsList density', () => {
  const ROWS = [ROW({ name: 'a' }), ROW({ name: 'b' })];

  it('comfortable: shows KindBadge, result-desc, result-meta; no result-sources', async () => {
    const { container } = await renderList({
      results: ROWS, groupBy: 'none', searchMode: 'all', query: '', searchTokens: [],
      dense: 'comfortable',
    });
    expect(container.querySelectorAll('.kind-badge').length).toBe(ROWS.length);
    expect(container.querySelectorAll('.result-desc').length).toBe(ROWS.length);
    expect(container.querySelectorAll('.result-meta').length).toBe(ROWS.length);
    expect(container.querySelectorAll('.result-sources').length).toBe(0);
  });

  it('compact: no KindBadge, no result-desc; result-meta still present', async () => {
    const { container } = await renderList({
      results: ROWS, groupBy: 'none', searchMode: 'all', query: '', searchTokens: [],
      dense: 'compact',
    });
    expect(container.querySelectorAll('.kind-badge').length).toBe(0);
    expect(container.querySelectorAll('.result-desc').length).toBe(0);
    expect(container.querySelectorAll('.result-meta').length).toBe(ROWS.length);
  });

  it('dense: no KindBadge, no result-desc, no result-meta', async () => {
    const { container } = await renderList({
      results: ROWS, groupBy: 'none', searchMode: 'all', query: '', searchTokens: [],
      dense: 'dense',
    });
    expect(container.querySelectorAll('.kind-badge').length).toBe(0);
    expect(container.querySelectorAll('.result-desc').length).toBe(0);
    expect(container.querySelectorAll('.result-meta').length).toBe(0);
  });
});

describe('ResultsList canonical ordering', () => {
  it('renders magnetic_field family in tier order (cluster mode)', async () => {
    // Insert in a deliberately wrong order; cmpOrderKey should reorder them.
    const shuffled = [
      MAGNETIC_FAMILY[6], MAGNETIC_FAMILY[3], MAGNETIC_FAMILY[1],
      MAGNETIC_FAMILY[5], MAGNETIC_FAMILY[0], MAGNETIC_FAMILY[4], MAGNETIC_FAMILY[2],
    ];
    const { container } = await renderList({
      results: shuffled,
      groupBy: 'cluster',
      searchMode: 'all',
      query: '',
      searchTokens: [],
    });
    // Grab every rendered result row's name. The DOM order should match
    // the canonical tier ordering.
    const rows = container.querySelectorAll('.result-row .result-name');
    const order = Array.from(rows).map((el) => el.textContent);
    expect(order).toEqual([
      'magnetic_field',
      'radial_magnetic_field',
      'toroidal_magnetic_field',
      'vertical_magnetic_field',
      'poloidal_magnetic_field',
      'magnetic_field_magnitude',
      'flux_surface_averaged_magnetic_field',
    ]);
  });
});

describe('ResultsList collapsible groups', () => {
  // Two rows in different categories to exercise multi-group behaviour.
  const TWO_CATS = [
    ROW({ name: 'equilibrium_name', category: 'equilibrium', group: 'g1' }),
    ROW({ name: 'transport_name',   category: 'transport',   group: 'g2' }),
  ];

  it('Outline button collapses all groups; Expand all re-expands them', async () => {
    const { container } = await renderList({
      results: TWO_CATS,
      groupBy: 'category',
      searchMode: 'all',
      query: '',
      searchTokens: [],
    });

    // Initially both rows should be visible.
    expect(container.querySelectorAll('.result-row').length).toBe(2);
    expect(container.querySelectorAll('.result-group-head').length).toBe(2);

    // Click "Outline" to collapse all.
    const outlineBtn = container.querySelector('.collapse-all');
    expect(outlineBtn).not.toBeNull();
    await act(async () => { fireEvent.click(outlineBtn); });

    // No result rows rendered; headings still present.
    expect(container.querySelectorAll('.result-row').length).toBe(0);
    expect(container.querySelectorAll('.result-group-head').length).toBe(2);
    expect(outlineBtn.textContent).toContain('Expand all');

    // Click "Expand all" to restore.
    await act(async () => { fireEvent.click(outlineBtn); });
    expect(container.querySelectorAll('.result-row').length).toBe(2);
    expect(outlineBtn.textContent).toContain('Outline');
  });

  it('clicking a single group header toggles only that group', async () => {
    const { container } = await renderList({
      results: TWO_CATS,
      groupBy: 'category',
      searchMode: 'all',
      query: '',
      searchTokens: [],
    });

    const heads = container.querySelectorAll('.result-group-head');
    expect(heads.length).toBe(2);

    // Collapse the first group.
    await act(async () => { fireEvent.click(heads[0]); });

    // One group is collapsed; the other still has its row.
    expect(container.querySelectorAll('.result-row').length).toBe(1);
    // Both headings remain.
    expect(container.querySelectorAll('.result-group-head').length).toBe(2);
  });

  it('re-clicking the active group-mode button resets collapsed state', async () => {
    // We need a controlled wrapper that owns groupBy so we can simulate
    // clicking the active "Domain" button while staying in category mode.
    const { useState: useStateOuter } = await import('react');

    function ControlledWrapper() {
      const [groupBy, setGroupBy] = useStateOuter('category');
      return (
        <DataProvider>
          <ResultsList
            results={TWO_CATS}
            selected={null}
            onSelect={() => {}}
            dense="comfortable"
            groupBy={groupBy}
            setGroupBy={setGroupBy}
            query=""
            searchTokens={[]}
            searchMode="all"
          />
        </DataProvider>
      );
    }

    // Import DataProvider for the wrapper.
    const { DataProvider: DP } = await import('../../src/lib/data.js');
    // Patch so mockFetch is set before render.
    mockFetch(TWO_CATS, [
      { id: 'equilibrium', label: 'Equilibrium', count: 0 },
      { id: 'transport', label: 'Transport', count: 0 },
    ]);

    let result;
    await act(async () => {
      result = render(<ControlledWrapper />);
      await new Promise((r) => setTimeout(r, 0));
    });
    const { container } = result;

    // Collapse one group.
    const heads = container.querySelectorAll('.result-group-head');
    await act(async () => { fireEvent.click(heads[0]); });
    expect(container.querySelectorAll('.result-row').length).toBe(1);

    // Click the active "Domain" (category) group-mode button.
    const groupBtns = container.querySelectorAll('.group-toggle button');
    // "Domain" is the second button (index 1).
    const domainBtn = [...groupBtns].find((b) => b.textContent === 'Domain');
    await act(async () => { fireEvent.click(domainBtn); });

    // Collapsed Set should be reset — both rows visible again.
    expect(container.querySelectorAll('.result-row').length).toBe(2);
  });

  it('aria-expanded on group headers matches rendered state', async () => {
    const { container } = await renderList({
      results: TWO_CATS,
      groupBy: 'category',
      searchMode: 'all',
      query: '',
      searchTokens: [],
    });

    const heads = container.querySelectorAll('.result-group-head');
    // All start expanded.
    for (const h of heads) {
      expect(h.getAttribute('aria-expanded')).toBe('true');
    }

    // Collapse the first.
    await act(async () => { fireEvent.click(heads[0]); });
    expect(heads[0].getAttribute('aria-expanded')).toBe('false');
    expect(heads[1].getAttribute('aria-expanded')).toBe('true');
  });
});
