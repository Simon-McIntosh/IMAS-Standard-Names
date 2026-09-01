import { describe, it, expect, vi } from 'vitest';
import { act, render, screen, fireEvent } from '@testing-library/react';
import { NameLink } from '../../src/components/NameLink.jsx';
import { DataProvider } from '../../src/lib/data.js';

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
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

const SAMPLE = {
  name: 'plasma_current',
  short: 'Toroidal plasma current',
  unit: 'A',
  kind: 'scalar',
  sources: [],
  parse: [],
  seeAlso: [],
};

describe('NameLink', () => {
  it('renders as a <span> (inline), not a <button>', async () => {
    const { container } = await renderWithData(
      <NameLink name="plasma_current" onSelect={() => {}} />,
      [SAMPLE],
    );
    const link = container.querySelector('.name-link');
    expect(link).not.toBeNull();
    expect(link.tagName).toBe('SPAN');
    expect(link.getAttribute('role')).toBe('link');
    expect(link.getAttribute('tabindex')).toBe('0');
    expect(link.getAttribute('data-name')).toBe('plasma_current');
  });

  it('uses humanised label when no explicit label is passed', async () => {
    const { container } = await renderWithData(
      <NameLink name="minor_radius_of_plasma_boundary" onSelect={() => {}} />,
      [],
    );
    const link = container.querySelector('.name-link');
    expect(link.textContent).toBe('minor radius of plasma boundary');
  });

  it('prefers an explicit label over the humanised name', async () => {
    const { container } = await renderWithData(
      <NameLink name="plasma_current" label="Ip" onSelect={() => {}} />,
      [SAMPLE],
    );
    expect(container.querySelector('.name-link').textContent).toBe('Ip');
  });

  it('encodes name, unit, and short in the title tooltip', async () => {
    const { container } = await renderWithData(
      <NameLink name="plasma_current" onSelect={() => {}} />,
      [SAMPLE],
    );
    const title = container.querySelector('.name-link').getAttribute('title');
    expect(title).toContain('plasma_current');
    expect(title).toContain('[A]');
    expect(title).toContain('Toroidal plasma current');
  });

  it('marks unknown names as missing with cursor:help and no role', async () => {
    const { container } = await renderWithData(
      <NameLink name="not_in_catalog" onSelect={() => {}} />,
      [],
    );
    const link = container.querySelector('.name-link');
    expect(link.className).toContain('missing');
    expect(link.getAttribute('role')).toBeNull();
    expect(link.getAttribute('tabindex')).toBeNull();
    expect(link.getAttribute('title')).toContain('Not yet in catalog');
  });

  it('calls onSelect on click', async () => {
    const onSelect = vi.fn();
    const { container } = await renderWithData(
      <NameLink name="plasma_current" onSelect={onSelect} />,
      [SAMPLE],
    );
    fireEvent.click(container.querySelector('.name-link'));
    expect(onSelect).toHaveBeenCalledWith('plasma_current');
  });

  it('calls onSelect on Enter and Space', async () => {
    const onSelect = vi.fn();
    const { container } = await renderWithData(
      <NameLink name="plasma_current" onSelect={onSelect} />,
      [SAMPLE],
    );
    const link = container.querySelector('.name-link');
    fireEvent.keyDown(link, { key: 'Enter' });
    fireEvent.keyDown(link, { key: ' ' });
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it('does not call onSelect when the target is missing', async () => {
    const onSelect = vi.fn();
    const { container } = await renderWithData(
      <NameLink name="not_in_catalog" onSelect={onSelect} />,
      [],
    );
    fireEvent.click(container.querySelector('.name-link'));
    expect(onSelect).not.toHaveBeenCalled();
  });
});
