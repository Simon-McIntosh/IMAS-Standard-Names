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

  it('header contains no h2, no stats element, and no "COLUMNS" text', async () => {
    const { container } = await renderMatrix([N('electron_pressure')]);
    expect(container.querySelector('h2')).toBeNull();
    expect(container.querySelector('.matrix-stats')).toBeNull();
    expect(container.textContent).not.toContain('COLUMNS');
  });

  it('renders all seven MATRIX_COLS as segmented-control buttons', async () => {
    const { getByText } = await renderMatrix([N('electron_pressure')]);
    for (const label of ['Axis', 'Locus', 'Operator', 'Reduction', 'Subject', 'Mechanism', 'Domain']) {
      expect(getByText(label)).toBeTruthy();
    }
  });

  it('grammar-segment active button carries --role-hue inline style', async () => {
    const { getByText, container } = await renderMatrix([N('electron_pressure')]);
    for (const label of ['Axis', 'Locus', 'Operator', 'Reduction', 'Subject', 'Mechanism']) {
      await act(async () => { fireEvent.click(getByText(label)); });
      const active = container.querySelector('.seg button.on');
      expect(active).not.toBeNull();
      expect(active.style.getPropertyValue('--role-hue')).not.toBe('');
    }
  });

  it('Domain active button does NOT carry --role-hue inline style', async () => {
    const { getByText, container } = await renderMatrix([N('electron_pressure')]);
    await act(async () => { fireEvent.click(getByText('Domain')); });
    const active = container.querySelector('.seg button.on');
    expect(active).not.toBeNull();
    expect(active.style.getPropertyValue('--role-hue')).toBe('');
    expect(active.hasAttribute('style')).toBeFalsy();
  });

  it('column and row header buttons have no title starting with "Filter Browse to"', async () => {
    const names = [
      N('electron_pressure', { base: 'pressure', parse: [{ role: 'base', text: 'pressure' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names);
    for (const btn of container.querySelectorAll('.matrix-col-btn, .matrix-row-btn')) {
      const t = btn.getAttribute('title') ?? '';
      expect(t.startsWith('Filter Browse to')).toBe(false);
    }
  });

  it('row label safety_factor renders as "safety factor"', async () => {
    const names = [
      N('safety_factor', { base: 'safety_factor', parse: [{ role: 'base', text: 'safety_factor' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names);
    const rowBtn = container.querySelector('.matrix-row-btn');
    expect(rowBtn).not.toBeNull();
    expect(rowBtn.textContent).toBe('safety factor');
  });

  it('locus column value "of_plasma_boundary" renders as "plasma boundary"; th title stays canonical', async () => {
    const names = [
      N('pressure_at_plasma_boundary', {
        base: 'pressure',
        parse: [{ role: 'base', text: 'pressure' }, { role: 'locus', text: 'of_plasma_boundary' }],
      }),
    ];
    const { getByText, container } = await renderMatrix(names);
    await act(async () => { fireEvent.click(getByText('Locus')); });
    const colBtn = container.querySelector('.matrix-col-btn');
    expect(colBtn).not.toBeNull();
    expect(colBtn.textContent).toBe('plasma boundary');
    const th = container.querySelector('.matrix-col');
    expect(th.getAttribute('title')).toBe('of_plasma_boundary');
  });

  it('clicking Mechanism column header sets process filter key (not mechanism)', async () => {
    const setFilters = vi.fn();
    const setView = vi.fn();
    const names = [
      N('electron_pressure_due_to_radiation', {
        base: 'pressure',
        parse: [{ role: 'base', text: 'pressure' }, { role: 'process', text: 'radiation' }],
      }),
    ];
    const { container, getByText } = await renderMatrix(names, [], { setFilters, setView });

    await act(async () => { fireEvent.click(getByText('Mechanism')); });

    const colBtn = container.querySelector('.matrix-col-btn');
    expect(colBtn).not.toBeNull();
    await act(async () => { fireEvent.click(colBtn); });

    expect(setFilters).toHaveBeenCalled();
    const updater = setFilters.mock.calls[0][0];
    const next = updater({ base: new Set(), process: new Set() });
    expect([...next.process]).toContain('radiation');
    expect(setView).toHaveBeenCalledWith('browse');
  });

  it('Subject column uses n.subject property when no parse token has role="subject"', async () => {
    const setFilters = vi.fn();
    const setView = vi.fn();
    const names = [
      N('electron_temperature', {
        base: 'temperature',
        parse: [{ role: 'base', text: 'temperature' }],
        subject: 'electron',
      }),
    ];
    const { container, getByText } = await renderMatrix(names, [], { setFilters, setView });

    await act(async () => { fireEvent.click(getByText('Subject')); });

    const colBtn = container.querySelector('.matrix-col-btn');
    expect(colBtn).not.toBeNull();
    await act(async () => { fireEvent.click(colBtn); });

    expect(setFilters).toHaveBeenCalled();
    const updater = setFilters.mock.calls[0][0];
    const next = updater({ base: new Set(), subject: new Set() });
    expect([...next.subject]).toContain('electron');
    expect(setView).toHaveBeenCalledWith('browse');
  });

  it('clicking row header invokes setFilters with canonical (un-prettified) value', async () => {
    const setFilters = vi.fn();
    const setView = vi.fn();
    const names = [
      N('safety_factor', { base: 'safety_factor', parse: [{ role: 'base', text: 'safety_factor' }, { role: 'axis', text: 'r' }] }),
    ];
    const { container } = await renderMatrix(names, [], { setFilters, setView });
    const rowBtn = container.querySelector('.matrix-row-btn');
    await act(async () => { fireEvent.click(rowBtn); });
    expect(setFilters).toHaveBeenCalled();
    const updater = setFilters.mock.calls[0][0];
    const next = updater({ base: new Set() });
    expect([...next.base]).toContain('safety_factor');
  });
});
