import { describe, it, expect, afterEach } from 'vitest';
import { act, render } from '@testing-library/react';
import App from '../../src/App.jsx';

// A review-batch build constrains the whole SPA to a fixed id-set. These
// tests render the full App against a mocked data.json and assert the
// result universe equals the batch — with no control to reveal the rest —
// while a normal build (no review_batch) shows every name.

const NAME = (over) => ({
  name: 'x',
  short: '',
  unit: 'T',
  algebra: 'scalar',
  status: 'active',
  sources: [],
  parse: [],
  seeAlso: [],
  category: 'equilibrium',
  group: 'g',
  ...over,
});

const FIVE = [
  NAME({ name: 'magnetic_field' }),
  NAME({ name: 'ion_temperature', category: 'core_plasma_physics' }),
  NAME({ name: 'electron_temperature', category: 'core_plasma_physics' }),
  NAME({ name: 'safety_factor' }),
  NAME({ name: 'plasma_current' }),
];

function mockFetch(extra) {
  globalThis.fetch = async (url) => {
    if (typeof url === 'string' && url.includes('data.json')) {
      return {
        ok: true,
        async json() {
          return {
            CATALOG_VERSION: 'test',
            CATEGORIES: [
              { id: 'equilibrium', label: 'Equilibrium', count: 0 },
              { id: 'core_plasma_physics', label: 'Core Plasma', count: 0 },
            ],
            GRAMMAR_VOCAB: {},
            STANDARD_TERMS: [],
            NAMES: FIVE,
            ...extra,
          };
        },
      };
    }
    return { ok: false };
  };
}

async function renderApp(extra) {
  mockFetch(extra);
  let result;
  await act(async () => {
    result = render(<App />);
    await new Promise((r) => setTimeout(r, 0));
  });
  return result;
}

function renderedNames(container) {
  return [...container.querySelectorAll('.result-name')].map((el) => el.textContent);
}

afterEach(() => {
  window.location.hash = '';
});

describe('review-batch fixed view', () => {
  it('constrains the universe to exactly the batch ids', async () => {
    const { container } = await renderApp({
      review_batch: ['ion_temperature', 'magnetic_field'],
    });
    const names = renderedNames(container).sort();
    expect(names).toEqual(['ion_temperature', 'magnetic_field']);
  });

  it('shows a batch banner and offers no control to reveal the rest', async () => {
    const { container } = await renderApp({
      review_batch: ['ion_temperature', 'magnetic_field'],
    });
    // The unobtrusive banner reports the batch size.
    expect(container.querySelector('.review-batch-banner')).not.toBeNull();
    // A fixed view: nothing anywhere offers to show the full catalog.
    const showAll = [...container.querySelectorAll('button, a')].filter((el) =>
      /show all|show full|full catalog|reveal/i.test(el.textContent || ''),
    );
    expect(showAll).toEqual([]);
  });

  it('renders every name when no review_batch is present', async () => {
    const { container } = await renderApp();
    const names = renderedNames(container).sort();
    expect(names).toEqual(
      [
        'electron_temperature',
        'ion_temperature',
        'magnetic_field',
        'plasma_current',
        'safety_factor',
      ].sort(),
    );
    expect(container.querySelector('.review-batch-banner')).toBeNull();
  });

  it('ignores an empty review_batch (behaves like a normal build)', async () => {
    const { container } = await renderApp({ review_batch: [] });
    expect(renderedNames(container).length).toBe(5);
    expect(container.querySelector('.review-batch-banner')).toBeNull();
  });
});
