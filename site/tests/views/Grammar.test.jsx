import { describe, it, expect } from 'vitest';
import { act, render, fireEvent } from '@testing-library/react';
import { Grammar } from '../../src/views/Grammar.jsx';
import { DataProvider } from '../../src/lib/data.js';

// A trimmed but structurally-faithful GRAMMAR_VOCAB — one entry list per
// segment, each entry an object carrying a `token` (and `kind`/`relations`
// where the composer needs them).
const VOCAB = {
  operators: [
    { token: 'magnitude', kind: 'unary_prefix' },
    { token: 'amplitude', kind: 'unary_postfix' },
  ],
  components: [{ token: 'poloidal' }, { token: 'radial' }, { token: 'toroidal' }],
  aggregations: [{ token: 'total' }],
  orbits: [{ token: 'trapped' }],
  populations: [{ token: 'fast' }],
  subjects: [{ token: 'electron' }, { token: 'ion' }],
  physical_bases: [
    { token: 'magnetic_field', kind: 'vector' },
    { token: 'pressure', kind: 'scalar' },
    { token: 'temperature', kind: 'scalar' },
  ],
  geometry_carriers: [{ token: 'centroid' }],
  locus_registry: [{ token: 'magnetic_axis', type: 'position', relations: ['at', 'of'] }],
  regions: [{ token: 'core_region' }],
  processes: [{ token: 'conduction' }],
  physics_domains: [{ token: 'equilibrium' }],
};

const N = (name, parse) => ({
  name,
  short: name.replace(/_/g, ' '),
  unit: '1',
  kind: 'scalar',
  sources: [],
  parse,
  seeAlso: [],
  category: 'equilibrium',
  group: 'default',
});

const NAMES = [
  N('temperature', [{ role: 'base', text: 'temperature' }]),
  N('electron_temperature', [
    { role: 'subject', text: 'electron' },
    { role: 'base', text: 'temperature' },
  ]),
  N('poloidal_magnetic_field', [
    { role: 'axis', text: 'poloidal' },
    { role: 'base', text: 'magnetic_field' },
  ]),
  N('radial_magnetic_field', [
    { role: 'axis', text: 'radial' },
    { role: 'base', text: 'magnetic_field' },
  ]),
  // The emitter renders the locus segment WITH its relation connector.
  N('safety_factor_at_magnetic_axis', [
    { role: 'base', text: 'safety_factor' },
    { role: 'locus', text: 'at_magnetic_axis' },
  ]),
];

function mockFetch() {
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return {
        CATALOG_VERSION: 'test',
        CATEGORIES: [],
        GRAMMAR_VOCAB: VOCAB,
        NAMES,
      };
    },
  });
}

async function renderGrammar(props = {}) {
  mockFetch();
  let result;
  await act(async () => {
    result = render(
      <DataProvider>
        <Grammar
          onSelect={props.onSelect ?? (() => {})}
          setView={props.setView ?? (() => {})}
          query={props.query ?? ''}
          seedName={props.seedName ?? null}
          seedNonce={props.seedNonce ?? 0}
        />
      </DataProvider>,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  return result;
}

describe('Grammar composer', () => {
  it('marks the root as data-active-view="grammar"', async () => {
    const { container } = await renderGrammar();
    const root = container.querySelector('.grammar-view');
    expect(root).not.toBeNull();
    expect(root.getAttribute('data-active-view')).toBe('grammar');
  });

  it('renders the eleven locked-order segment nodes', async () => {
    const { container } = await renderGrammar();
    const nodes = container.querySelectorAll('.gx-chain .gx-node');
    expect(nodes.length).toBe(11);
    const labels = [...nodes].map((n) => n.querySelector('.gx-node-label').textContent);
    expect(labels).toEqual([
      'operator', 'component', 'coordinate', 'aggregation', 'orbit',
      'population', 'subject', 'physical base', 'geometric base', 'locus', 'process',
    ]);
  });

  it('starts with the physical base active and the geometric base inactive', async () => {
    const { container } = await renderGrammar();
    const byLabel = (label) =>
      [...container.querySelectorAll('.gx-node')].find(
        (n) => n.querySelector('.gx-node-label').textContent === label,
      );
    expect(byLabel('physical base').className).toContain('is-on');
    expect(byLabel('geometric base').className).not.toContain('is-on');
  });

  it('keeps a base mandatory — clicking the active base does not remove it', async () => {
    const { container } = await renderGrammar();
    const base = [...container.querySelectorAll('.gx-node')].find(
      (n) => n.querySelector('.gx-node-label').textContent === 'physical base',
    );
    await act(async () => { fireEvent.click(base); });
    expect(base.className).toContain('is-on');
  });

  it('seeds the builder from a name and composes it back', async () => {
    const { container } = await renderGrammar({ seedName: 'poloidal_magnetic_field', seedNonce: 1 });
    // The base token slot is filled with the seeded base.
    const filled = [...container.querySelectorAll('.gx-tok.is-filled .mono')].map((s) => s.textContent);
    expect(filled).toContain('magnetic_field');
    expect(filled).toContain('poloidal');
    // The composed name round-trips and is flagged as an existing catalog hit.
    const hit = container.querySelector('.gx-name.is-hit');
    expect(hit).not.toBeNull();
    expect(hit.textContent).toBe('poloidal_magnetic_field');
  });

  it('narrows the results list to names matching the composition', async () => {
    const { container } = await renderGrammar({ seedName: 'poloidal_magnetic_field', seedNonce: 1 });
    const names = [...container.querySelectorAll('.gx-list .gx-name')].map((b) => b.textContent);
    expect(names).toContain('poloidal_magnetic_field');
    // radial_magnetic_field shares the base but not the poloidal component.
    expect(names).not.toContain('radial_magnetic_field');
  });

  it('seeds a locus (stripping its relation connector) and exposes the at|of switch', async () => {
    const { container } = await renderGrammar({ seedName: 'safety_factor_at_magnetic_axis', seedNonce: 1 });
    const filled = [...container.querySelectorAll('.gx-tok.is-filled .mono')].map((s) => s.textContent);
    // The bare registry token is recovered from the `at_…` parse text.
    expect(filled).toContain('magnetic_axis');
    // A position locus admits at|of, so the connector renders as a switch
    // showing the relation actually used in the name.
    const sw = container.querySelector('.gx-relsw');
    expect(sw).not.toBeNull();
    expect(sw.textContent).toContain('at');
    // The composed name round-trips to the seeded catalog entry.
    const hit = container.querySelector('.gx-name.is-hit');
    expect(hit?.textContent).toBe('safety_factor_at_magnetic_axis');
  });
});
