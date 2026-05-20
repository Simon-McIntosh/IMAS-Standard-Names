import { describe, it, expect, vi } from 'vitest';
import { act, render, fireEvent } from '@testing-library/react';
import { VocabularyMatrix } from '../../src/views/Matrix.jsx';
import { DataProvider } from '../../src/lib/data.js';

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

async function renderMatrix(names, categories = [], props = {}) {
  mockFetch(names, categories);
  let result;
  await act(async () => {
    result = render(
      <DataProvider>
        <VocabularyMatrix
          onSelect={props.onSelect ?? (() => {})}
          setFilters={props.setFilters ?? (() => {})}
          setView={props.setView ?? (() => {})}
        />
      </DataProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

const N = (name, over = {}) => ({
  name,
  short: name,
  unit: '1',
  kind: 'scalar',
  sources: [],
  parse: [{ role: 'base', text: over.base ?? 'pressure' }, ...(over.parse ?? [])],
  seeAlso: [],
  category: over.category ?? 'equilibrium',
  group: over.group ?? 'default',
  ...over,
});

describe('VocabularyMatrix', () => {
  it('marks the root as data-active-view="matrix"', async () => {
    const { container } = await renderMatrix([N('electron_pressure')]);
    const root = container.querySelector('.matrix-view');
    expect(root).not.toBeNull();
    expect(root.getAttribute('data-active-view')).toBe('matrix');
  });

  it('renders exactly one active-view root in the subtree', async () => {
    const { container } = await renderMatrix([N('electron_pressure')]);
    expect(container.querySelectorAll('[data-active-view]').length).toBe(1);
  });

  it('switching the column segmented control recomputes the matrix without remount', async () => {
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }], category: 'core_profiles' }),
      N('ion_pressure',      { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'locus', text: 'pedestal' }], category: 'core_profiles' }),
    ];
    const { container, getByText } = await renderMatrix(names);

    const axisBefore = container.querySelector('.matrix-table');
    expect(axisBefore).not.toBeNull();

    await act(async () => {
      fireEvent.click(getByText('Locus'));
    });

    const axisAfter = container.querySelector('.matrix-table');
    expect(axisAfter).not.toBeNull();
    expect(axisAfter).toBe(axisBefore);
  });

  it('clicking a filled cell opens a popover with the correct name list', async () => {
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
      N('ion_pressure',      { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names);

    const filled = container.querySelector('.matrix-cell.filled');
    expect(filled).not.toBeNull();
    await act(async () => { fireEvent.click(filled); });

    const popover = container.querySelector('.matrix-popover');
    expect(popover).not.toBeNull();
    expect(popover.textContent).toContain('electron_pressure');
    expect(popover.textContent).toContain('ion_pressure');
  });

  it('clicking a name in the popover calls onSelect with that name', async () => {
    const onSelect = vi.fn();
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names, [], { onSelect });

    const filled = container.querySelector('.matrix-cell.filled');
    await act(async () => { fireEvent.click(filled); });

    const item = container.querySelector('.matrix-popover-item');
    expect(item).not.toBeNull();
    await act(async () => { fireEvent.click(item); });

    expect(onSelect).toHaveBeenCalledWith('electron_pressure');
  });

  it('clicking a row header calls setFilters with a base Set and setView browse', async () => {
    const setFilters = vi.fn();
    const setView = vi.fn();
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names, [], { setFilters, setView });

    const rowBtn = container.querySelector('.matrix-row-btn');
    expect(rowBtn).not.toBeNull();
    await act(async () => { fireEvent.click(rowBtn); });

    expect(setFilters).toHaveBeenCalled();
    const updater = setFilters.mock.calls[0][0];
    const prev = { base: new Set(), axis: new Set() };
    const next = updater(prev);
    expect([...next.base]).toContain('pressure');

    expect(setView).toHaveBeenCalledWith('browse');
  });

  it('clicking a column header calls setFilters with the facet Set and setView browse', async () => {
    const setFilters = vi.fn();
    const setView = vi.fn();
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names, [], { setFilters, setView });

    const colBtn = container.querySelector('.matrix-col-btn');
    expect(colBtn).not.toBeNull();
    await act(async () => { fireEvent.click(colBtn); });

    expect(setFilters).toHaveBeenCalled();
    const updater = setFilters.mock.calls[0][0];
    const prev = { base: new Set(), axis: new Set() };
    const next = updater(prev);
    expect([...next.axis]).toContain('r');

    expect(setView).toHaveBeenCalledWith('browse');
  });

  it('stats element shows count × dimensions and does not contain a percentage or "coverage"', async () => {
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
      N('ion_pressure',      { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names);

    const stats = container.querySelector('.matrix-stats');
    expect(stats).not.toBeNull();
    expect(stats.textContent).toMatch(/\d+ named entries/);
    expect(stats.textContent).toMatch(/\d+×\d+ shown/);
    expect(stats.textContent).not.toContain('%');
    expect(stats.textContent).not.toContain('coverage');
  });
});
