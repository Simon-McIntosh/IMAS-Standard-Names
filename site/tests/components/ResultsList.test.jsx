import { describe, it, expect } from 'vitest';
import { act, render } from '@testing-library/react';
import { ResultsList } from '../../src/components/ResultsList.jsx';
import { DataProvider } from '../../src/lib/data.js';

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

async function renderList({ results, groupBy, searchMode, query, searchTokens }) {
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
          dense="comfortable"
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
  kind: 'scalar',
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
