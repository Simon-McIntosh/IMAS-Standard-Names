import { describe, expect, it } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { Filters } from '../../src/components/Filters.jsx';
import { DataProvider } from '../../src/lib/data.js';

function renderFilters(opts = {}) {
  const filters = opts.filters ?? {
    category: new Set(),
    kind: new Set(),
    unit: new Set(),
    source_status: new Set(),
    ids: new Set(),
  };
  const faceted = opts.faceted ?? {
    units: [['T', 5]],
    kinds: { scalar: 3, vector: 2 },
    source_statuses: { composed: 4 },
    idses: [['equilibrium', 4]],
  };
  const allCounts = opts.allCounts ?? { category: { equilibrium: 5 } };
  return render(
    <DataProvider>
      <Filters filters={filters} setFilters={() => {}} faceted={faceted} allCounts={allCounts} />
    </DataProvider>,
  );
}

describe('Filters', () => {
  it('renders four group headings by default (Domain, Kind, Unit, Advanced)', async () => {
    await act(async () => {
      renderFilters();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // FilterGroup renders a button for each group header.
    const headers = screen.getAllByRole('button');
    const titles = headers.map((b) => b.textContent.replace(/[▾▸]/g, '').trim());
    const groups = titles.filter((t) =>
      ['Domain', 'Kind', 'Unit', 'Advanced'].includes(t),
    );
    expect(groups.sort()).toEqual(['Advanced', 'Domain', 'Kind', 'Unit']);
  });

  it('hides kind rows with count 0', async () => {
    await act(async () => {
      render(
        <DataProvider>
          <Filters
            filters={{
              category: new Set(),
              kind: new Set(),
              unit: new Set(),
              source_status: new Set(),
              ids: new Set(),
            }}
            setFilters={() => {}}
            faceted={{
              units: [],
              kinds: { scalar: 3, vector: 0, tensor: 0, complex: 0, metadata: 0 },
              source_statuses: {},
              idses: [],
            }}
            allCounts={{ category: {} }}
          />
        </DataProvider>,
      );
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(screen.queryByText('Scalar')).toBeInTheDocument();
    expect(screen.queryByText('Vector')).not.toBeInTheDocument();
    expect(screen.queryByText('Tensor')).not.toBeInTheDocument();
  });
});
