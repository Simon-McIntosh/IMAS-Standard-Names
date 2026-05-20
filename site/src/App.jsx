import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { DataProvider, useData } from './lib/data.js';
import { useUrlState } from './lib/url-state.js';
import { useTweaks } from './hooks/useTweaks.js';
import { useChildIndex, useGroupIndex } from './lib/indexes.js';
import { setMermaidTheme } from './lib/mermaid.js';
import { tokenize, searchNames } from './lib/search.js';
import { Header } from './components/Header.jsx';
import { Browse } from './views/Browse.jsx';
import { VocabularyMatrix } from './views/Matrix.jsx';

// Lazy-load the dev tweaks panel — it never lands in the default bundle.
const DevTweaks = lazy(() => import('./components/DevTweaks.jsx'));

function tweaksEnabled() {
  if (typeof location === 'undefined') return false;
  return new URLSearchParams(location.search).get('tweaks') === '1';
}

function LoadingScreen() {
  return (
    <div
      style={{
        height: '100vh',
        display: 'grid',
        placeItems: 'center',
        color: 'var(--text-2)',
        fontFamily: 'var(--font-sans)',
        fontSize: '13px',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '24px', marginBottom: '12px', opacity: 0.6 }}>◐</div>
        <div>Loading catalog…</div>
      </div>
    </div>
  );
}

function ErrorScreen({ error }) {
  return (
    <div
      style={{
        height: '100vh',
        display: 'grid',
        placeItems: 'center',
        color: 'var(--text)',
        fontFamily: 'var(--font-sans)',
        padding: '24px',
      }}
    >
      <div style={{ textAlign: 'center', maxWidth: 480 }}>
        <div style={{ fontSize: '24px', marginBottom: '12px' }}>⚠</div>
        <div style={{ fontWeight: 600, marginBottom: '8px' }}>
          Failed to load catalog
        </div>
        <div style={{ color: 'var(--text-2)', fontSize: '12.5px', marginBottom: '16px' }}>
          {error?.message || 'Could not fetch data.json from this URL.'}
        </div>
        <button
          className="icon-btn"
          style={{ width: 'auto', padding: '0 16px', height: '32px' }}
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    </div>
  );
}

const PARSE_FILTER_KEYS = [
  'base', 'operator', 'reduction', 'modifier',
  'axis', 'locus', 'subject',
];

function Shell() {
  const { NAMES, loading, error } = useData();
  const [urlState, setUrlState] = useUrlState();
  const [query, setQuery] = useState(urlState.query);
  const [filters, setFilters] = useState({
    category:  new Set(),
    unit:      new Set(),
    kind:      new Set(),
    lifecycle: new Set(),
    base:      new Set(),
    operator:  new Set(),
    reduction: new Set(),
    modifier:  new Set(),
    axis:      new Set(),
    locus:     new Set(),
    subject:   new Set(),
  });
  const [selected, setSelected] = useState(urlState.name);
  const [view, setView] = useState(urlState.view);
  const [tweaks, setTweak] = useTweaks();

  const childIndex = useChildIndex(NAMES);
  const groupIndex = useGroupIndex(NAMES);

  // Sync state → URL.
  useEffect(() => {
    setUrlState({ view, name: selected, query });
  }, [view, selected, query, setUrlState]);

  // Dev-only height guard: if the active view ever paints with zero
  // height the flex sizing regressed. Fire once per view change.
  useEffect(() => {
    if (typeof import.meta !== 'undefined' && import.meta.env?.PROD) return;
    const id = requestAnimationFrame(() => {
      const v = document.querySelector('[data-active-view]');
      if (v && v.offsetHeight === 0) {
        // eslint-disable-next-line no-console
        console.error('[route] active view has 0 height', v);
      }
    });
    return () => cancelAnimationFrame(id);
  }, [view]);

  // Apply theme + accent.
  useEffect(() => {
    document.documentElement.dataset.theme = tweaks.theme;
    document.documentElement.style.setProperty('--accent', tweaks.accent);
    setMermaidTheme(tweaks.theme);
  }, [tweaks.theme, tweaks.accent]);

  // Apply facet filters first (cheap, exact), then route the free-text
  // query through `searchNames` (tokenised, weighted, AND across tokens).
  // The previous OR'd-substring scan let "pressure" match unrelated rows
  // via incidental char-cluster overlap.
  const searchTokens = useMemo(() => tokenize(query), [query]);
  const { results, searchMode } = useMemo(() => {
    const filtered = NAMES.filter((n) => {
      if (filters.category.size && !filters.category.has(n.category)) return false;
      if (filters.kind.size && !filters.kind.has(n.algebra || 'scalar')) return false;
      if (filters.lifecycle.size && !filters.lifecycle.has(n.status || 'active')) return false;
      if (filters.unit.size && !filters.unit.has(n.unit)) return false;
      const anyParseFilter = PARSE_FILTER_KEYS.some((k) => filters[k].size > 0);
      if (anyParseFilter) {
        const parse = n.parse || [];
        for (const k of PARSE_FILTER_KEYS) {
          if (filters[k].size === 0) continue;
          const matchesAll = [...filters[k]].every((text) =>
            parse.some((tok) => tok.role === k && tok.text === text),
          );
          if (!matchesAll) return false;
        }
      }
      return true;
    });
    const search = searchNames(filtered, searchTokens);
    // When `searchNames` falls through to fuzzy (or has no query at all)
    // alphabetical order is what users expect; the scored path retains
    // its score-desc / name-length-asc tie-break ordering.
    if (search.mode === 'scored') {
      return { results: search.results, searchMode: search.mode };
    }
    return {
      results: search.results.slice().sort((a, b) => a.name.localeCompare(b.name)),
      searchMode: search.mode,
    };
  }, [searchTokens, filters, NAMES]);

  // Facet counts over the FULL corpus — stable as the user toggles filters.
  const faceted = useMemo(() => {
    const units = {};
    const kinds = {};
    const lifecycle = {};
    for (const n of NAMES) {
      units[n.unit] = (units[n.unit] || 0) + 1;
      const kind = n.algebra || 'scalar';
      kinds[kind] = (kinds[kind] || 0) + 1;
      const lc = n.status || 'active';
      lifecycle[lc] = (lifecycle[lc] || 0) + 1;
    }
    return {
      units: Object.entries(units).sort((a, b) => b[1] - a[1]),
      kinds,
      lifecycle,
      totalSources: NAMES.reduce((s, n) => s + n.sources.length, 0),
    };
  }, [NAMES]);

  const allCounts = useMemo(() => {
    const category = {};
    for (const n of NAMES) category[n.category] = (category[n.category] || 0) + 1;
    return { category };
  }, [NAMES]);

  // Keyboard nav: ↑↓ traverses `results`; Escape clears selection.
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT') return;
      if (e.key === 'Escape') {
        setSelected(null);
        return;
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const idx = results.findIndex((r) => r.name === selected);
        const next =
          e.key === 'ArrowDown'
            ? Math.min(results.length - 1, idx + 1)
            : Math.max(0, idx - 1);
        if (results[next]) {
          setSelected(results[next].name);
          e.preventDefault();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [results, selected]);

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen error={error} />;

  return (
    <div className="app">
      <Header
        query={query}
        setQuery={setQuery}
        theme={tweaks.theme}
        setTheme={(t) => setTweak('theme', t)}
        dense={tweaks.density}
        setDense={(d) => setTweak('density', d)}
        view={view}
        setView={setView}
      />
      {view === 'browse' ? (
        <Browse
          filters={filters}
          setFilters={setFilters}
          view={view}
          setView={setView}
          faceted={faceted}
          allCounts={allCounts}
          results={results}
          selected={selected}
          setSelected={setSelected}
          dense={tweaks.density}
          groupBy={tweaks.groupBy}
          setGroupBy={(v) => setTweak('groupBy', v)}
          childIndex={childIndex}
          groupIndex={groupIndex}
          query={query}
          searchTokens={searchTokens}
          searchMode={searchMode}
        />
      ) : (
        <VocabularyMatrix
          onSelect={(name) => { setSelected(name); setView('browse'); }}
          setFilters={setFilters}
          setView={setView}
        />
      )}
      {tweaksEnabled() && (
        <Suspense fallback={null}>
          <DevTweaks tweaks={tweaks} setTweak={setTweak} />
        </Suspense>
      )}
    </div>
  );
}

export default function App() {
  return (
    <DataProvider>
      <Shell />
    </DataProvider>
  );
}
