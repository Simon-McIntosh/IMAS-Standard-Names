import React, { createContext, useContext, useEffect, useState } from 'react';

// Runtime data loader and React context.
//
// `data.json` is loaded at runtime via `fetch('./data.json')` so the SPA
// bundle is independent of the dataset; the Python emitter writes a
// `data.json` alongside the SPA build at deploy time. Optionally a
// `versions.json` file may sit one level up (mike's standard format) so
// the SPA can render a version selector — its absence is silent.

const EMPTY = {
  CATALOG_VERSION: '',
  CATEGORIES: [],
  GRAMMAR_VOCAB: {},
  NAMES: [],
};

const DataContext = createContext({
  ...EMPTY,
  loading: true,
  error: null,
  versions: null,
});

export function useData() {
  return useContext(DataContext);
}

export function DataProvider({ children }) {
  const [state, setState] = useState({
    ...EMPTY,
    loading: true,
    error: null,
    versions: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch('./data.json', { cache: 'no-cache' });
        if (!res.ok) throw new Error(`fetch failed: HTTP ${res.status}`);
        const data = await res.json();
        // Background-load versions.json. 404 is silent — most deployments
        // are unversioned single-folder builds.
        let versions = null;
        try {
          const vres = await fetch('../versions.json', { cache: 'no-cache' });
          if (vres.ok) versions = await vres.json();
        } catch {
          /* ignore */
        }
        if (cancelled) return;
        setState({
          CATALOG_VERSION: data.CATALOG_VERSION ?? '',
          CATEGORIES: Array.isArray(data.CATEGORIES) ? data.CATEGORIES : [],
          GRAMMAR_VOCAB: data.GRAMMAR_VOCAB ?? {},
          NAMES: Array.isArray(data.NAMES) ? data.NAMES : [],
          loading: false,
          error: null,
          versions,
        });
      } catch (err) {
        if (cancelled) return;
        setState((s) => ({ ...s, loading: false, error: err }));
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return React.createElement(DataContext.Provider, { value: state }, children);
}
