import { useEffect, useRef } from 'react';
import { useData } from '../lib/data.js';
import { VersionSwitcher } from './VersionSwitcher.jsx';

// Top-bar: brand, search, view-segment (Browse | Map), density-segment
// (≡ ☰ ⩬), theme toggle. ⌘K / Ctrl+K focuses the search input from
// anywhere in the app.
export function Header({
  query, setQuery, theme, setTheme, dense, setDense, view, setView,
}) {
  const inp = useRef(null);
  const { CATALOG_VERSION, versions } = useData();

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inp.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />
            <ellipse cx="12" cy="12" rx="6" ry="10" stroke="currentColor" strokeWidth="1.2" />
            <ellipse cx="12" cy="12" rx="10" ry="3" stroke="currentColor" strokeWidth="1.2" />
          </svg>
        </div>
        <div className="brand-text">
          <div className="brand-title">IMAS Standard Names</div>
          <div className="brand-sub">{CATALOG_VERSION}</div>
        </div>
      </div>

      <div className="search-wrap">
        <svg className="search-ic" width="14" height="14" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.6" />
          <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
        <input
          ref={inp}
          className="search-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          spellCheck="false"
          placeholder="Search names, descriptions, units, sources…"
        />
        <kbd className="search-kbd">⌘K</kbd>
      </div>

      <div className="header-actions">
        <VersionSwitcher versions={versions} current={CATALOG_VERSION} />
        <div className="seg view-seg">
          <button
            className={view === 'browse' ? 'on' : ''}
            onClick={() => setView('browse')}
            title="Browse names"
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            Browse
          </button>
          <button
            className={view === 'map' ? 'on' : ''}
            onClick={() => setView('map')}
            title="Lineage map"
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4" />
              <circle cx="2.5" cy="3" r="1.4" stroke="currentColor" strokeWidth="1.4" />
              <circle cx="13.5" cy="3" r="1.4" stroke="currentColor" strokeWidth="1.4" />
              <circle cx="2.5" cy="13" r="1.4" stroke="currentColor" strokeWidth="1.4" />
              <circle cx="13.5" cy="13" r="1.4" stroke="currentColor" strokeWidth="1.4" />
              <path d="M3.5 4l3.2 3M12.5 4L9.3 7M3.5 12l3.2-3M12.5 12L9.3 9" stroke="currentColor" strokeWidth="1.2" />
            </svg>
            Map
          </button>
        </div>
        <div className="seg">
          <button className={dense === 'comfortable' ? 'on' : ''} onClick={() => setDense('comfortable')} title="Comfortable">≡</button>
          <button className={dense === 'compact' ? 'on' : ''} onClick={() => setDense('compact')} title="Compact">☰</button>
          <button className={dense === 'dense' ? 'on' : ''} onClick={() => setDense('dense')} title="Dense">⩬</button>
        </div>
        <button
          className="icon-btn"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title="Toggle theme"
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>
      </div>
    </header>
  );
}
