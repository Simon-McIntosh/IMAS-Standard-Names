import { describe, expect, it } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { Filters } from '../../src/components/Filters.jsx';
import { DataProvider } from '../../src/lib/data.js';

function renderFilters(opts = {}) {
  const filters = opts.filters ?? {
    category: new Set(),
    kind: new Set(),
    lifecycle: new Set(),
    unit: new Set(),
  };
  const faceted = opts.faceted ?? {
    units: [['T', 5]],
    kinds: { scalar: 3, vector: 2 },
    lifecycle: { active: 4, draft: 2 },
  };
  const allCounts = opts.allCounts ?? { category: { equilibrium: 5 } };
  return render(
    <DataProvider>
      <Filters filters={filters} setFilters={() => {}} faceted={faceted} allCounts={allCounts} />
    </DataProvider>,
  );
}

describe('Filters', () => {
  it('renders four group headings by default (Domain, Kind, Lifecycle, Unit)', async () => {
    await act(async () => {
      renderFilters();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // FilterGroup renders a button for each group header.
    const headers = screen.getAllByRole('button');
    const titles = headers.map((b) => b.textContent.replace(/[▾▸]/g, '').trim());
    const groups = titles.filter((t) =>
      ['Domain', 'Kind', 'Lifecycle', 'Unit'].includes(t),
    );
    expect(groups.sort()).toEqual(['Domain', 'Kind', 'Lifecycle', 'Unit']);
  });

  it('does not render an Advanced disclosure group', async () => {
    await act(async () => {
      renderFilters();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    const headers = screen.queryAllByRole('button');
    const titles = headers.map((b) => b.textContent.replace(/[▾▸]/g, '').trim());
    expect(titles).not.toContain('Advanced');
  });

  it('renders lifecycle rows with coloured swatches for non-zero statuses', async () => {
    await act(async () => {
      renderFilters({
        faceted: {
          units: [],
          kinds: {},
          lifecycle: { active: 3, draft: 1, deprecated: 2, superseded: 1 },
        },
      });
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // Each lifecycle row has a .lifecycle-swatch element.
    const swatches = document.querySelectorAll('.lifecycle-swatch');
    expect(swatches.length).toBe(4);
    // Swatch classes cover all four statuses.
    const classes = Array.from(swatches).map((s) => s.className);
    expect(classes.some((c) => c.includes('lifecycle-active'))).toBe(true);
    expect(classes.some((c) => c.includes('lifecycle-draft'))).toBe(true);
    expect(classes.some((c) => c.includes('lifecycle-deprecated'))).toBe(true);
    expect(classes.some((c) => c.includes('lifecycle-superseded'))).toBe(true);
  });

  it('hides lifecycle rows with count 0', async () => {
    await act(async () => {
      renderFilters({
        faceted: {
          units: [],
          kinds: {},
          lifecycle: { active: 3, draft: 0 },
        },
      });
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // Only the active swatch should be present.
    const swatches = document.querySelectorAll('.lifecycle-swatch');
    expect(swatches.length).toBe(1);
  });

  it('hides kind rows with count 0', async () => {
    await act(async () => {
      render(
        <DataProvider>
          <Filters
            filters={{
              category: new Set(),
              kind: new Set(),
              lifecycle: new Set(),
              unit: new Set(),
            }}
            setFilters={() => {}}
            faceted={{
              units: [],
              kinds: { scalar: 3, vector: 0, tensor: 0, complex: 0, metadata: 0 },
              lifecycle: {},
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
