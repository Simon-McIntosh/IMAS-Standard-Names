import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { DetailPanel } from '../../src/components/DetailPanel.jsx';
import { DataProvider } from '../../src/lib/data.js';

// Use a mock fetch that returns a single catalog entry so DetailPanel
// can render the hero.
const MOCK_ENTRY = {
  name: 'electron_temperature',
  category: 'transport',
  group: 'temperature',
  parent: null,
  algebra: 'scalar',
  unit: 'eV',
  tags: [],
  short: 'Test description',
  long: 'Long documentation goes here',
  sign: null,
  seeAlso: [],
  arguments: [],
  sources: [],
  parse: [],
  components: [],
  magnitude: null,
  children: [],
};

describe('DetailPanel sticky strip', () => {
  it('renders the .detail-sticky strip with kind badge + name + close', async () => {
    // Override fetch mock so this test has a real entry to render.
    const origFetch = global.fetch;
    global.fetch = (url) => {
      if (url.includes('data.json')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            CATALOG_VERSION: 'test',
            CATEGORIES: [{ id: 'transport', label: 'Transport', count: 1 }],
            GRAMMAR_VOCAB: {},
            NAMES: [MOCK_ENTRY],
          }),
        });
      }
      return Promise.resolve({ ok: false });
    };
    try {
      const { container, findByText } = render(
        <DataProvider>
          <DetailPanel
            name="electron_temperature"
            onSelect={() => {}}
            onClose={() => {}}
            childIndex={{}}
            groupIndex={{}}
          />
        </DataProvider>
      );
      // Wait for the hero h1 to appear (multiple elements share the name text,
      // so query by role+class rather than bare text).
      await findByText('Test description');
      const sticky = container.querySelector('.detail-sticky');
      expect(sticky).not.toBeNull();
      const stickyName = sticky.querySelector('.detail-sticky-name');
      expect(stickyName?.textContent).toBe('electron_temperature');
      // Sticky strip has its own close button.
      const stickyClose = sticky.querySelector('.detail-sticky-close');
      expect(stickyClose).not.toBeNull();
    } finally {
      global.fetch = origFetch;
    }
  });

  it('does not set .detail-scrolled by default (hero in viewport)', async () => {
    // Use the existing setup.js mock; we just need to confirm there's
    // no detail-scrolled class on the container at mount.
    const origFetch = global.fetch;
    global.fetch = (url) => {
      if (url.includes('data.json')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            CATALOG_VERSION: 'test',
            CATEGORIES: [{ id: 'transport', label: 'Transport', count: 1 }],
            GRAMMAR_VOCAB: {},
            NAMES: [MOCK_ENTRY],
          }),
        });
      }
      return Promise.resolve({ ok: false });
    };
    try {
      const { container, findByText } = render(
        <DataProvider>
          <DetailPanel
            name="electron_temperature"
            onSelect={() => {}}
            onClose={() => {}}
            childIndex={{}}
            groupIndex={{}}
          />
        </DataProvider>
      );
      // Wait for content to render (use unique short description text).
      await findByText('Test description');
      // IntersectionObserver does not run in jsdom; .detail-scrolled
      // remains absent. Verify the toggle class is not pre-set.
      const detail = container.querySelector('.detail');
      expect(detail).not.toBeNull();
      expect(detail.classList.contains('detail-scrolled')).toBe(false);
    } finally {
      global.fetch = origFetch;
    }
  });
});
