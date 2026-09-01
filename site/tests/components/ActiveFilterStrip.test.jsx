import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { ActiveFilterStrip } from '../../src/components/ActiveFilterStrip.jsx';

function emptyFilters() {
  return {
    category: new Set(),
    unit:     new Set(),
    kind:     new Set(),
    lifecycle:new Set(),
    base:     new Set(),
    operator: new Set(),
    reduction:new Set(),
    modifier: new Set(),
    axis:     new Set(),
    locus:    new Set(),
    subject:  new Set(),
  };
}

describe('ActiveFilterStrip', () => {
  it('renders nothing when no filters are active', () => {
    const { container } = render(
      <ActiveFilterStrip filters={emptyFilters()} setFilters={() => {}} />
    );
    expect(container.querySelector('.active-filters')).toBeNull();
  });

  it('renders one pill per active value across keys', () => {
    const f = emptyFilters();
    f.locus.add('plasma_boundary');
    f.locus.add('magnetic_axis');
    f.unit.add('eV');
    f.subject.add('electron');
    const { container } = render(
      <ActiveFilterStrip filters={f} setFilters={() => {}} />
    );
    const pills = container.querySelectorAll('.active-filter-pill');
    expect(pills.length).toBe(4);
  });

  it('clicking × removes that single value, leaving the rest', () => {
    const f = emptyFilters();
    f.locus.add('plasma_boundary');
    f.locus.add('magnetic_axis');
    f.unit.add('eV');
    let next = null;
    const setFilters = (updater) => { next = updater(f); };
    const { container } = render(
      <ActiveFilterStrip filters={f} setFilters={setFilters} />
    );
    const evPill = Array.from(container.querySelectorAll('.active-filter-pill'))
      .find((el) => el.textContent.includes('eV'));
    evPill.querySelector('.active-filter-pill-x').click();
    expect(next.unit.has('eV')).toBe(false);
    expect(next.locus.has('plasma_boundary')).toBe(true);
    expect(next.locus.has('magnetic_axis')).toBe(true);
  });

  it('shows Clear all when >=2 pills present', () => {
    const f = emptyFilters();
    f.locus.add('plasma_boundary');
    f.unit.add('eV');
    const { container } = render(
      <ActiveFilterStrip filters={f} setFilters={() => {}} />
    );
    expect(container.querySelector('.active-filters-clear')).not.toBeNull();
  });

  it('hides Clear all when only 1 pill is present', () => {
    const f = emptyFilters();
    f.locus.add('plasma_boundary');
    const { container } = render(
      <ActiveFilterStrip filters={f} setFilters={() => {}} />
    );
    expect(container.querySelector('.active-filters-clear')).toBeNull();
  });

  it('Clear all sweeps every key', () => {
    const f = emptyFilters();
    f.locus.add('plasma_boundary');
    f.unit.add('eV');
    f.subject.add('electron');
    let next = null;
    const setFilters = (updater) => { next = updater(f); };
    const { container } = render(
      <ActiveFilterStrip filters={f} setFilters={setFilters} />
    );
    container.querySelector('.active-filters-clear').click();
    for (const key of Object.keys(next)) {
      expect(next[key].size).toBe(0);
    }
  });
});
