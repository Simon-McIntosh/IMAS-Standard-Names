import { describe, it, expect } from 'vitest';
import { act, render, fireEvent } from '@testing-library/react';
import { Grammar } from '../../src/views/Grammar.jsx';
import { DataProvider } from '../../src/lib/data.js';

// Faithful (trimmed) GRAMMAR_VOCAB — the composer reads these sections.
const VOCAB = {
  operators: [{ token: 'magnitude', kind: 'unary_postfix' }],
  components: [{ token: 'poloidal' }, { token: 'radial' }],
  physical_bases: [
    { token: 'magnetic_field' },
    { token: 'power' },
    { token: 'temperature' },
    { token: 'radius' },
  ],
  geometry_carriers: [{ token: 'flux_loop_carrier' }],
  locus_registry: [{ token: 'flux_loop', type: 'entity', relations: ['of'] }],
  regions: [],
  aggregations: [{ token: 'total' }],
  orbits: [],
  populations: [],
  subjects: [{ token: 'electron' }],
  // Genuine generic qualifiers, each with its emitted category (no subjects).
  qualifiers: [
    { token: 'external', category: 'state' },
    { token: 'heating', category: 'engineering' },
    { token: 'major', category: 'geometry' },
    { token: 'minor', category: 'geometry' },
  ],
};

const N = (name, parse) => ({
  name, short: name.replace(/_/g, ' '), unit: '1', kind: 'scalar',
  sources: [], parse, seeAlso: [], category: 'equilibrium', group: 'default',
});

const NAMES = [
  N('total_external_heating_power', [
    { role: 'aggregation', text: 'total' },
    { role: 'qualifier', text: 'external' },
    { role: 'qualifier', text: 'heating' },
    { role: 'base', text: 'power' },
  ]),
  N('major_radius_of_flux_loop', [
    { role: 'qualifier', text: 'major' },
    { role: 'base', text: 'radius' },
    { role: 'locus', text: 'of_flux_loop' },
  ]),
  N('poloidal_magnetic_field', [
    { role: 'axis', text: 'poloidal' },
    { role: 'base', text: 'magnetic_field' },
  ]),
];

function mockFetch() {
  globalThis.fetch = async () => ({
    ok: true,
    async json() {
      return { CATALOG_VERSION: 'test', CATEGORIES: [], GRAMMAR_VOCAB: VOCAB, NAMES };
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

const filledTokens = (c) =>
  [...c.querySelectorAll('.gx-namebar .gx-tok.is-filled .mono')].map((s) => s.textContent);

describe('Grammar composer', () => {
  it('marks the root as data-active-view="grammar"', async () => {
    const { container } = await renderGrammar();
    const root = container.querySelector('.grammar-view');
    expect(root?.getAttribute('data-active-view')).toBe('grammar');
  });

  it('renders the rail with a single unified qualifier node + base alt-pair', async () => {
    const { container } = await renderGrammar();
    const labels = [...container.querySelectorAll('.gx-chain .gx-node-label')].map((n) => n.textContent);
    expect(labels).toEqual([
      'operator', 'component', 'coordinate', 'qualifier',
      'physical base', 'geometric base', 'locus', 'process',
    ]);
  });

  it('decomposes total_external_heating_power into ordered qualifiers and round-trips (was: fabricated total_power_due_to_heating)', async () => {
    const { container } = await renderGrammar({ seedName: 'total_external_heating_power', seedNonce: 1 });
    // All four tokens present, in order — nothing dropped, nothing invented.
    expect(filledTokens(container)).toEqual(['total', 'external', 'heating', 'power']);
    // The composition round-trips and is flagged as a real catalog hit.
    const hit = container.querySelector('.gx-name.is-hit');
    expect(hit?.textContent).toBe('total_external_heating_power');
    // The cross-view "STANDARD NAME ↗" link is present (name exists).
    expect(container.querySelector('.gx-comp-k.is-link')).not.toBeNull();
  });

  it('keeps the major qualifier and locus on major_radius_of_flux_loop (was: dropped to radius_of_flux_loop)', async () => {
    const { container } = await renderGrammar({ seedName: 'major_radius_of_flux_loop', seedNonce: 1 });
    expect(filledTokens(container)).toEqual(['major', 'radius', 'flux_loop']);
    expect(container.querySelector('.gx-name.is-hit')?.textContent).toBe('major_radius_of_flux_loop');
  });

  const railLabels = (c) => [...c.querySelectorAll('.gx-chain .gx-node-label')].map((n) => n.textContent);
  const pickInDropdown = (c, tok) => {
    const row = [...c.querySelectorAll('.gx-dd .gx-dd-row')].find(
      (r) => r.querySelector('.gx-dd-tok')?.textContent === tok,
    );
    return act(async () => { fireEvent.click(row); });
  };

  it('clicking a top-row segment button adds it and opens the picker below the STANDARD NAME row', async () => {
    const { container } = await renderGrammar();
    const processNode = [...container.querySelectorAll('.gx-chain .gx-node')].find(
      (n) => n.querySelector('.gx-node-label').textContent === 'process',
    );
    await act(async () => { fireEvent.click(processNode); });
    // The segment chip is added in the STANDARD NAME row AND its picker opens.
    expect([...container.querySelectorAll('.gx-namebar .gx-tok-ph')].map((e) => e.textContent)).toContain('process');
    expect(container.querySelector('.gx-dd')).not.toBeNull();
  });

  it('qualifier + adds a placeholder instance and opens a grouped (single-select) picker', async () => {
    const { container } = await renderGrammar();
    const qAdd = [...container.querySelectorAll('.gx-chain .gx-node')].find(
      (n) => n.querySelector('.gx-node-label').textContent === 'qualifier',
    );
    await act(async () => { fireEvent.click(qAdd); });
    // Placeholder qualifier chip appears in the lower row; grouped picker opens.
    expect([...container.querySelectorAll('.gx-namebar .gx-tok-ph')].map((e) => e.textContent)).toContain('qualifier');
    const dd = container.querySelector('.gx-dd');
    expect(dd).not.toBeNull();
    const groupHeaders = [...dd.querySelectorAll('.gx-dd-grouph')].map((g) => g.firstChild.textContent.trim());
    expect(groupHeaders).toEqual(expect.arrayContaining(['aggregation', 'subject', 'geometry', 'state']));
    // Single-select now (one instance per pick) — no multi tick column.
    expect(dd.querySelector('.gx-dd-check')).toBeNull();
  });

  it('picking a qualifier relabels its top button to the group; clicking the top button removes it', async () => {
    const { container } = await renderGrammar();
    const addQual = async () => {
      const qAdd = [...container.querySelectorAll('.gx-chain .gx-node')].find(
        (n) => n.querySelector('.gx-node-label').textContent === 'qualifier',
      );
      await act(async () => { fireEvent.click(qAdd); });
    };
    await addQual();
    await pickInDropdown(container, 'external'); // category: state
    await addQual();
    await pickInDropdown(container, 'major'); // category: geometry

    // Tokens land in the STANDARD NAME row in selection order…
    expect(filledTokens(container)).toEqual(['external', 'major']);
    // …and each qualifier's top-row button is labelled by its GROUP, not "qualifier".
    expect(railLabels(container)).toEqual(expect.arrayContaining(['state', 'geometry']));
    expect(container.querySelector('.gx-add-q')).toBeNull(); // no inline '+'

    // Clicking the group button removes that qualifier.
    const stateBtn = [...container.querySelectorAll('.gx-chain .gx-node')].find(
      (n) => n.querySelector('.gx-node-label').textContent === 'state',
    );
    await act(async () => { fireEvent.click(stateBtn); });
    expect(filledTokens(container)).toEqual(['major']);
    expect(railLabels(container)).not.toContain('state');
  });

  it('narrows results to names matching the seeded composition', async () => {
    const { container } = await renderGrammar({ seedName: 'poloidal_magnetic_field', seedNonce: 1 });
    const names = [...container.querySelectorAll('.gx-list .gx-name')].map((b) => b.textContent);
    expect(names).toEqual(['poloidal_magnetic_field']);
  });
});
