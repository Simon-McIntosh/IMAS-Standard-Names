import '@testing-library/jest-dom/vitest';

global.fetch = (url) => {
  if (typeof url === 'string' && url.includes('data.json')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          CATALOG_VERSION: 'test',
          CATEGORIES: [{ id: 'equilibrium', label: 'Equilibrium', count: 5 }],
          GRAMMAR_VOCAB: {},
          NAMES: [],
        }),
    });
  }
  if (typeof url === 'string' && url.includes('versions.json')) {
    return Promise.resolve({ ok: false });
  }
  return Promise.resolve({ ok: false });
};
