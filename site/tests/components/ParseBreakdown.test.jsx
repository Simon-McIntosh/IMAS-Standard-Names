import { describe, it, expect } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { ParseBreakdown } from '../../src/components/ParseBreakdown.jsx';
import { DataProvider } from '../../src/lib/data.js';

// ParseBreakdown is wrapped in DataProvider so useData() resolves cleanly.
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
      <ParseBreakdown name="poloidal_magnetic_field" parse={parse} filters={{}} setFilters={() => {}} />,
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
      <ParseBreakdown name="plasma_current" parse={parse} filters={{}} setFilters={() => {}} />,
    );
    expect(screen.getByText('<subject> · <base>')).toBeInTheDocument();
  });

  it('renders every role the dataset emitter produces', async () => {
    // Every role value emitted by dataset.py `_derive_grammar_facets`
    // MUST resolve to a non-"Unknown" label in the SPA.
    const parse = [
      { role: 'operator', text: 'magnitude' },
      { role: 'axis', text: 'toroidal' },
      { role: 'qualifier', text: 'major' },
      { role: 'base', text: 'radius' },
      { role: 'locus', text: 'of_plasma_boundary' },
      { role: 'process', text: 'due_to_radiation' },
      { role: 'unparseable', text: 'foo_bar' },
    ];
    await renderWithData(
      <ParseBreakdown name="anything" parse={parse} filters={{}} setFilters={() => {}} />,
    );
    expect(screen.getByText('Operator')).toBeInTheDocument();
    expect(screen.getByText('Axis')).toBeInTheDocument();
    expect(screen.getByText('Qualifier')).toBeInTheDocument();
    expect(screen.getByText('Base')).toBeInTheDocument();
    expect(screen.getByText('Locus')).toBeInTheDocument();
    expect(screen.getByText('Process')).toBeInTheDocument();
    expect(screen.getByText('Unparseable')).toBeInTheDocument();
    // The bug we're regression-testing: 'qualifier' must NOT render as Unknown.
    expect(screen.queryByText('Unknown')).toBeNull();
  });

  it('falls back to a plain mono source string when parse is empty', async () => {
    await renderWithData(
      <ParseBreakdown name="orphaned_name" parse={[]} filters={{}} setFilters={() => {}} />,
    );
    expect(screen.getByText('orphaned_name')).toBeInTheDocument();
  });

  it('renders the + glyph on every filterable role token', async () => {
    const parse = [
      { role: 'base',     text: 'temperature' },
      { role: 'axis',     text: 'poloidal' },
      { role: 'locus',    text: 'plasma_boundary' },
      { role: 'preposition', text: 'at' },   // not filterable
    ];
    const { container } = await renderWithData(
      <ParseBreakdown
        name="temperature_at_plasma_boundary"
        parse={parse}
        filters={{ base: new Set(), axis: new Set(), locus: new Set(),
                   operator: new Set(), reduction: new Set(),
                   modifier: new Set(), subject: new Set() }}
        setFilters={() => {}}
      />,
    );
    expect(container.querySelector('.gtoken-base .gtoken-filter-glyph')).not.toBeNull();
    expect(container.querySelector('.gtoken-axis .gtoken-filter-glyph')).not.toBeNull();
    expect(container.querySelector('.gtoken-locus .gtoken-filter-glyph')).not.toBeNull();
    // Preposition is NOT filterable — no glyph.
    expect(container.querySelector('.gtoken-preposition .gtoken-filter-glyph')).toBeNull();
  });

  it('clicking a filterable token toggles its filter set', async () => {
    let last = null;
    const setFilters = (updater) => { last = updater({ base: new Set(), axis: new Set(), locus: new Set(), operator: new Set(), reduction: new Set(), modifier: new Set(), subject: new Set() }); };
    const parse = [{ role: 'base', text: 'temperature' }];
    const { container } = await renderWithData(
      <ParseBreakdown
        name="temperature"
        parse={parse}
        filters={{ base: new Set(), axis: new Set(), locus: new Set(), operator: new Set(), reduction: new Set(), modifier: new Set(), subject: new Set() }}
        setFilters={setFilters}
      />,
    );
    const chip = container.querySelector('.gtoken-base');
    chip.click();
    expect(last.base.has('temperature')).toBe(true);
  });

  it('clicking an active filter token removes it (is-filter-active branch)', async () => {
    let last = null;
    const initial = { base: new Set(['temperature']), axis: new Set(), locus: new Set(), operator: new Set(), reduction: new Set(), modifier: new Set(), subject: new Set() };
    const setFilters = (updater) => { last = updater(initial); };
    const parse = [{ role: 'base', text: 'temperature' }];
    const { container } = await renderWithData(
      <ParseBreakdown name="temperature" parse={parse} filters={initial} setFilters={setFilters} />,
    );
    const chip = container.querySelector('.gtoken-base');
    expect(chip.className).toContain('is-filter-active');
    chip.click();
    expect(last.base.has('temperature')).toBe(false);
  });

  it('non-filterable role (preposition) has no click handler effect on filters', async () => {
    let called = false;
    const setFilters = () => { called = true; };
    const parse = [{ role: 'preposition', text: 'of' }];
    const { container } = await renderWithData(
      <ParseBreakdown
        name="of"
        parse={parse}
        filters={{ base: new Set(), axis: new Set(), locus: new Set(), operator: new Set(), reduction: new Set(), modifier: new Set(), subject: new Set() }}
        setFilters={setFilters}
      />,
    );
    container.querySelector('.gtoken-preposition').click();
    expect(called).toBe(false);
  });
});
