import { describe, it, expect } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { ParseBreakdown } from '../../src/components/ParseBreakdown.jsx';
import { DataProvider } from '../../src/lib/data.js';

// ParseBreakdown reads NAMES from useData() to decide which tokens are
// clickable. We replace fetch() with a stub that returns a small NAMES
// list before mounting.
function mockFetch(names) {
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return { CATALOG_VERSION: 'test', CATEGORIES: [], GRAMMAR_VOCAB: {}, NAMES: names };
    },
  });
}

async function renderWithData(jsx, names = []) {
  mockFetch(names);
  let result;
  await act(async () => {
    result = render(<DataProvider>{jsx}</DataProvider>);
    // Let the DataProvider's fetch microtask settle.
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

describe('ParseBreakdown', () => {
  it('renders one chip per parse token with role label and text', async () => {
    const parse = [
      { role: 'axis', text: 'poloidal', note: 'vector component axis' },
      { role: 'base', text: 'magnetic_field', note: 'base quantity' },
    ];
    const { container } = await renderWithData(
      <ParseBreakdown name="poloidal_magnetic_field" parse={parse} onSelect={() => {}} />,
    );
    // Role labels are unique — chips only.
    expect(screen.getByText('Axis')).toBeInTheDocument();
    expect(screen.getByText('Base')).toBeInTheDocument();
    // Token text appears in BOTH the source-string overlay and the chip — find
    // the chip-scoped copy.
    const axisChip = container.querySelector('.gtoken-axis .gtoken-text');
    const baseChip = container.querySelector('.gtoken-base .gtoken-text');
    expect(axisChip).toHaveTextContent('poloidal');
    expect(baseChip).toHaveTextContent('magnetic_field');
  });

  it('emits a production footer joining roles with " · "', async () => {
    const parse = [
      { role: 'subject', text: 'plasma' },
      { role: 'base', text: 'current' },
    ];
    await renderWithData(
      <ParseBreakdown name="plasma_current" parse={parse} onSelect={() => {}} />,
    );
    expect(screen.getByText('<subject> · <base>')).toBeInTheDocument();
  });

  it('renders all nine roles when present', async () => {
    const parse = [
      { role: 'reduction', text: 'volume_averaged' },
      { role: 'modifier', text: 'total' },
      { role: 'subject', text: 'plasma' },
      { role: 'axis', text: 'toroidal' },
      { role: 'base', text: 'magnetic_field' },
      { role: 'operator', text: 'magnitude' },
      { role: 'preposition', text: 'at' },
      { role: 'locus', text: 'magnetic_axis' },
      { role: 'unknown', text: 'foo' },
    ];
    await renderWithData(
      <ParseBreakdown name="anything" parse={parse} onSelect={() => {}} />,
    );
    expect(screen.getByText('Reduction')).toBeInTheDocument();
    expect(screen.getByText('Modifier')).toBeInTheDocument();
    expect(screen.getByText('Subject')).toBeInTheDocument();
    expect(screen.getByText('Axis')).toBeInTheDocument();
    expect(screen.getByText('Base')).toBeInTheDocument();
    expect(screen.getByText('Operator')).toBeInTheDocument();
    expect(screen.getByText('Preposition')).toBeInTheDocument();
    expect(screen.getByText('Locus')).toBeInTheDocument();
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('falls back to a plain mono source string when parse is empty', async () => {
    await renderWithData(
      <ParseBreakdown name="orphaned_name" parse={[]} onSelect={() => {}} />,
    );
    expect(screen.getByText('orphaned_name')).toBeInTheDocument();
  });

  it('marks a base token as clickable when the target name exists', async () => {
    const parse = [
      { role: 'axis', text: 'poloidal' },
      { role: 'base', text: 'magnetic_field' },
    ];
    const { container } = await renderWithData(
      <ParseBreakdown name="poloidal_magnetic_field" parse={parse} onSelect={() => {}} />,
      [
        // a NAMES entry matching the base token — should make it clickable
        { name: 'magnetic_field', sources: [], parse: [], seeAlso: [] },
      ],
    );
    const base = container.querySelector('.gtoken-base');
    expect(base?.className).toContain('clickable');
  });
});
