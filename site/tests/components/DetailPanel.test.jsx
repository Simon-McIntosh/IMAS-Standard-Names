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
  status: 'active',
  unit: 'eV',
  tags: [],
  short: 'Test description',
  long: 'Long documentation goes here',
  sign: null,
  seeAlso: [],
  arguments: [],
  sources: [],
  superseded_by: null,
  deprecates: null,
  parse: [],
  components: [],
  magnitude: null,
  children: [],
};

function makeDataset(entry) {
  return {
    CATALOG_VERSION: 'test',
    CATEGORIES: [{ id: 'transport', label: 'Transport', count: 1 }],
    GRAMMAR_VOCAB: {},
    NAMES: [entry],
  };
}

function mockFetch(dataset) {
  return (url) => {
    if (url.includes('data.json')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(dataset),
      });
    }
    return Promise.resolve({ ok: false });
  };
}

describe('DetailPanel sticky strip', () => {
  it('renders the .detail-sticky strip with kind badge + name + close', async () => {
    const origFetch = global.fetch;
    global.fetch = mockFetch(makeDataset(MOCK_ENTRY));
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
      await findByText('Test description');
      const sticky = container.querySelector('.detail-sticky');
      expect(sticky).not.toBeNull();
      const stickyName = sticky.querySelector('.detail-sticky-name');
      expect(stickyName?.textContent).toBe('electron_temperature');
      const stickyClose = sticky.querySelector('.detail-sticky-close');
      expect(stickyClose).not.toBeNull();
    } finally {
      global.fetch = origFetch;
    }
  });

  it('does not set .detail-scrolled by default (hero in viewport)', async () => {
    const origFetch = global.fetch;
    global.fetch = mockFetch(makeDataset(MOCK_ENTRY));
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
      await findByText('Test description');
      const detail = container.querySelector('.detail');
      expect(detail).not.toBeNull();
      expect(detail.classList.contains('detail-scrolled')).toBe(false);
    } finally {
      global.fetch = origFetch;
    }
  });
});

describe('DetailPanel lifecycle banner', () => {
  it('active entry renders no lifecycle banner', async () => {
    const origFetch = global.fetch;
    global.fetch = mockFetch(makeDataset({ ...MOCK_ENTRY, status: 'active' }));
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
      await findByText('Test description');
      expect(container.querySelector('.detail-lifecycle-banner')).toBeNull();
    } finally {
      global.fetch = origFetch;
    }
  });

  it('draft entry renders state-draft banner', async () => {
    const origFetch = global.fetch;
    global.fetch = mockFetch(makeDataset({ ...MOCK_ENTRY, status: 'draft' }));
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
      await findByText('Test description');
      const banner = container.querySelector('.detail-lifecycle-banner.state-draft');
      expect(banner).not.toBeNull();
    } finally {
      global.fetch = origFetch;
    }
  });

  it('deprecated entry renders state-deprecated banner without successor link', async () => {
    const origFetch = global.fetch;
    global.fetch = mockFetch(makeDataset({
      ...MOCK_ENTRY,
      status: 'deprecated',
      superseded_by: 'some_other_name',
    }));
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
      await findByText('Test description');
      const banner = container.querySelector('.detail-lifecycle-banner.state-deprecated');
      expect(banner).not.toBeNull();
      // Deprecated entries must NOT show a NameLink to superseded_by —
      // deprecation has no committed replacement.
      expect(banner.textContent).not.toContain('some_other_name');
    } finally {
      global.fetch = origFetch;
    }
  });

  it('superseded entry renders state-superseded banner with clickable successor', async () => {
    const origFetch = global.fetch;
    const selected = [];
    global.fetch = mockFetch(makeDataset({
      ...MOCK_ENTRY,
      status: 'superseded',
      superseded_by: 'new_temperature',
    }));
    try {
      const { container, findByText } = render(
        <DataProvider>
          <DetailPanel
            name="electron_temperature"
            onSelect={(name) => selected.push(name)}
            onClose={() => {}}
            childIndex={{}}
            groupIndex={{}}
          />
        </DataProvider>
      );
      await findByText('Test description');
      const banner = container.querySelector('.detail-lifecycle-banner.state-superseded');
      expect(banner).not.toBeNull();
      // The successor name must appear — NameLink renders it humanised
      // (underscores → spaces) so query by data-name attribute.
      const link = banner.querySelector('[data-name="new_temperature"]');
      expect(link).not.toBeNull();
    } finally {
      global.fetch = origFetch;
    }
  });
});
