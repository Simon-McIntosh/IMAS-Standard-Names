import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { NeighborhoodGraph } from '../../src/components/NeighborhoodGraph.jsx';
import { DataProvider } from '../../src/lib/data.js';

// The DataProvider fetch mock in tests/setup.js returns NAMES: []
// — so `useData().NAMES.find(...)` always returns undefined.
// That's exactly the condition we want to test for "parent doesn't
// resolve" — it must NOT render a Parent row.

function renderNb(n, opts = {}) {
  return render(
    <DataProvider>
      <NeighborhoodGraph
        n={n}
        onSelect={() => {}}
        childIndex={opts.childIndex ?? {}}
        groupIndex={opts.groupIndex ?? {}}
      />
    </DataProvider>
  );
}

describe('NeighborhoodGraph parent resolution', () => {
  it('omits Parent row when parent name does not resolve to a real catalog entry', async () => {
    const n = {
      name: 'electron_temperature',
      category: 'transport',
      group: 'temperature',
      parent: 'nonexistent_parent_xyz',
      algebra: 'scalar',
      unit: 'eV',
      sources: [],
      seeAlso: [],
    };
    const { findByText, queryByText } = renderNb(n);
    // The "no neighborhood" empty state should appear because parent is
    // null, cluster/children/seeAlso are empty.
    await findByText(/no recorded parents/i);
    expect(queryByText('Parent')).not.toBeInTheDocument();
  });
});

describe('NeighborhoodGraph see-also filtering', () => {
  it('drops unresolved see-also entries before rendering chips', async () => {
    const n = {
      name: 'foo',
      category: 'x',
      group: 'g',
      parent: null,
      algebra: 'scalar',
      unit: '1',
      sources: [],
      seeAlso: ['unresolved_a', 'unresolved_b'],
    };
    const { findByText, queryByText } = renderNb(n);
    await findByText(/no recorded parents/i);
    // Neither "unresolved_a" nor "unresolved_b" should appear.
    expect(queryByText(/unresolved_a/)).not.toBeInTheDocument();
    expect(queryByText(/unresolved_b/)).not.toBeInTheDocument();
  });
});
