import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { DataProvider, useData } from './lib/data.js';
import { useUrlState } from './lib/url-state.js';
import { useTweaks } from './hooks/useTweaks.js';
import { useChildIndex, useGroupIndex } from './lib/indexes.js';
import { setMermaidTheme } from './lib/mermaid.js';
import { tokenize, searchNames } from './lib/search.js';
import { Header } from './components/Header.jsx';
import { Browse } from './views/Browse.jsx';
import { LineageMap } from './views/Map.jsx';

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

function Shell() {
  const { NAMES, loading, error } = useData();
  const [urlState, setUrlState] = useUrlState();
  const [query, setQuery] = useState(urlState.query);
  const [filters, setFilters] = useState({
    category: new Set(),
    unit: new Set(),
    kind: new Set(),
    status: new Set(),
    ids: new Set(),
    system: new Set(),
  });
  const [selected, setSelected] = useState(urlState.name);
  const [view, setView] = useState(urlState.view);
  const [mapCategory, setMapCategory] = useState(null);
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
      if (filters.unit.size && !filters.unit.has(n.unit)) return false;
      if (filters.kind.size && !filters.kind.has(n.kind)) return false;
      if (filters.status.size && !n.sources.some((s) => filters.status.has(s.status))) {
        return false;
      }
      if (filters.ids.size && !n.sources.some((s) => filters.ids.has(s.path.split('/')[0]))) {
        return false;
      }
      // `system` filter has no functional effect — UI only.
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
    const statuses = {};
    const idses = {};
    for (const n of NAMES) {
      units[n.unit] = (units[n.unit] || 0) + 1;
      kinds[n.kind] = (kinds[n.kind] || 0) + 1;
      for (const s of n.sources) {
        statuses[s.status] = (statuses[s.status] || 0) + 1;
        const root = s.path.split('/')[0];
        idses[root] = (idses[root] || 0) + 1;
      }
    }
    return {
      units: Object.entries(units).sort((a, b) => b[1] - a[1]),
      kinds,
      statuses,
      idses: Object.entries(idses).sort((a, b) => b[1] - a[1]).slice(0, 20),
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
        <LineageMap
          onSelect={(name) => {
            setSelected(name);
            setView('browse');
          }}
          activeCategory={mapCategory}
          setActiveCategory={setMapCategory}
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
