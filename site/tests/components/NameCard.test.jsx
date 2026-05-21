import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { NameCard } from '../../src/components/NameCard.jsx';

const N = {
  name: 'electron_temperature',
  algebra: 'scalar',
  unit: 'eV',
  short: 'Electron temperature',
};

describe('NameCard density', () => {
  it('comfortable renders kind-badge, desc, and edge label when edgeLabel is supplied', () => {
    const { container } = render(
      <NameCard n={N} onSelect={() => {}} relation="sibling" edgeLabel="axis = r" dense="comfortable" />
    );
    expect(container.querySelector('.kind-badge')).not.toBeNull();
    expect(container.querySelector('.nb-card-desc')).not.toBeNull();
    expect(container.querySelector('.nb-card-edge')).not.toBeNull();
  });

  it('compact renders kind-badge and desc but suppresses edge label', () => {
    const { container } = render(
      <NameCard n={N} onSelect={() => {}} relation="sibling" edgeLabel="axis = r" dense="compact" />
    );
    expect(container.querySelector('.kind-badge')).not.toBeNull();
    expect(container.querySelector('.nb-card-desc')).not.toBeNull();
    expect(container.querySelector('.nb-card-edge')).toBeNull();
  });

  it('dense renders only the name span — no badge, no unit-pill, no desc, no edge', () => {
    const { container } = render(
      <NameCard n={N} onSelect={() => {}} relation="sibling" edgeLabel="axis = r" dense="dense" />
    );
    expect(container.querySelector('.kind-badge')).toBeNull();
    expect(container.querySelector('.unit-pill')).toBeNull();
    expect(container.querySelector('.nb-card-desc')).toBeNull();
    expect(container.querySelector('.nb-card-edge')).toBeNull();
    expect(container.querySelector('.nb-card-name')).not.toBeNull();
  });
});
