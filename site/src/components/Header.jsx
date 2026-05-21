import { useEffect, useMemo, useRef, useState } from 'react';
import { useData } from '../lib/data.js';
import { VersionSwitcher } from './VersionSwitcher.jsx';

// Detect the current version from the URL path.
// gh-pages serves under /<repo>/<version>/ — extract the version segment.
function detectCurrentVersion() {
  const segs = location.pathname.split('/').filter(Boolean);
  // Look for common repo-name segment; version follows it.
  const repoIdx = segs.findIndex((s) =>
    s === 'imas-standard-names-catalog' || s === 'imas-standard-names'
  );
  if (repoIdx >= 0 && segs[repoIdx + 1]) return segs[repoIdx + 1];
  // Fallback: last segment is the version directory.
  return segs[segs.length - 1] || 'main';
}

// Top-bar: brand, search, view-segment (Browse | Matrix), density-segment
// (list-row SVGs), settings menu with theme picker. ⌘K / Ctrl+K focuses
// the search input from anywhere in the app.
export function Header({
  query, setQuery, theme, setTheme, dense, setDense, view, setView,
}) {
  const inp = useRef(null);
  const settingsRef = useRef(null);
  const { NAMES, versions } = useData();
  const currentVersion = useMemo(detectCurrentVersion, []);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const onVersionSelect = (v) => {
    // Navigate to the selected version, preserving deep-link hash.
    const base = location.pathname.replace(/\/[^/]+\/?$/, '/');
    location.href = `${base}${v.version}/${location.hash}`;
  };

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

  useEffect(() => {
    if (!settingsOpen) return;
    const onDown = (e) => {
      if (!settingsRef.current?.contains(e.target)) setSettingsOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [settingsOpen]);

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark">
          <img src="./imas-logo.png" alt="IMAS" width="32" height="32" />
        </div>
        <div className="brand-text">
          <div className="brand-title">Standard Names</div>
          <div className="brand-sub">
            {versions && (
              <VersionSwitcher
                versions={versions}
                current={currentVersion}
                onSelect={onVersionSelect}
              />
            )}
            {versions && <span className="brand-sep">·</span>}
            <span>{NAMES.length} names</span>
          </div>
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
        <div className="seg view-seg">
          <button
            className={view === 'browse' ? 'on' : ''}
            onClick={() => setView('browse')}
            title="Browse names"
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="2" y="2"  width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none"/>
              <rect x="9" y="2"  width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none"/>
              <rect x="2" y="9"  width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none"/>
              <rect x="9" y="9"  width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.4" fill="none"/>
            </svg>
            Browse
          </button>
          <button
            className={view === 'matrix' ? 'on' : ''}
            onClick={() => setView('matrix')}
            title="Vocabulary map (base × facet matrix)"
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="2"   y="2"   width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="6.5" y="2"   width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="11"  y="2"   width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="2"   y="6.5" width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="6.5" y="6.5" width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="11"  y="6.5" width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="2"   y="11"  width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="6.5" y="11"  width="3" height="3" rx="0.6" fill="currentColor"/>
              <rect x="11"  y="11"  width="3" height="3" rx="0.6" fill="currentColor"/>
            </svg>
            Matrix
          </button>
        </div>
        <div className="seg density-seg">
          <button
            className={dense === 'comfortable' ? 'on' : ''}
            onClick={() => setDense('comfortable')}
            title="Comfortable — name + description"
            aria-label="Comfortable density"
          >
            <svg width="18" height="14" viewBox="0 0 24 18" fill="none" aria-hidden="true">
              <rect x="1.5" y="1.5"  width="21" height="6.5" rx="1.4" stroke="currentColor" strokeWidth="1.1" fill="none" opacity="0.7"/>
              <rect x="3.5" y="3.4"  width="9"  height="1.2" rx="0.4" fill="currentColor"/>
              <rect x="3.5" y="5.3"  width="15" height="0.9" rx="0.3" fill="currentColor" opacity="0.5"/>
              <rect x="1.5" y="10"   width="21" height="6.5" rx="1.4" stroke="currentColor" strokeWidth="1.1" fill="none" opacity="0.7"/>
              <rect x="3.5" y="11.9" width="9"  height="1.2" rx="0.4" fill="currentColor"/>
              <rect x="3.5" y="13.8" width="15" height="0.9" rx="0.3" fill="currentColor" opacity="0.5"/>
            </svg>
          </button>
          <button
            className={dense === 'compact' ? 'on' : ''}
            onClick={() => setDense('compact')}
            title="Compact — name only, card rows"
            aria-label="Compact density"
          >
            <svg width="18" height="14" viewBox="0 0 24 18" fill="none" aria-hidden="true">
              <rect x="1.5" y="1.5"  width="21" height="4" rx="1.1" stroke="currentColor" strokeWidth="1.1" fill="none" opacity="0.7"/>
              <rect x="3.5" y="3.0"  width="9"  height="1.1" rx="0.4" fill="currentColor"/>
              <rect x="1.5" y="7"    width="21" height="4" rx="1.1" stroke="currentColor" strokeWidth="1.1" fill="none" opacity="0.7"/>
              <rect x="3.5" y="8.5"  width="9"  height="1.1" rx="0.4" fill="currentColor"/>
              <rect x="1.5" y="12.5" width="21" height="4" rx="1.1" stroke="currentColor" strokeWidth="1.1" fill="none" opacity="0.7"/>
              <rect x="3.5" y="14"   width="9"  height="1.1" rx="0.4" fill="currentColor"/>
            </svg>
          </button>
          <button
            className={dense === 'dense' ? 'on' : ''}
            onClick={() => setDense('dense')}
            title="Dense — packed name-only rows"
            aria-label="Dense (name only)"
          >
            <svg width="18" height="14" viewBox="0 0 24 18" fill="none" aria-hidden="true">
              <rect x="1.5" y="2"    width="21" height="2.4" rx="0.7" fill="currentColor" opacity="0.85"/>
              <rect x="1.5" y="5.4"  width="21" height="2.4" rx="0.7" fill="currentColor" opacity="0.85"/>
              <rect x="1.5" y="8.8"  width="21" height="2.4" rx="0.7" fill="currentColor" opacity="0.85"/>
              <rect x="1.5" y="12.2" width="21" height="2.4" rx="0.7" fill="currentColor" opacity="0.85"/>
              <rect x="1.5" y="15.6" width="21" height="1.4" rx="0.5" fill="currentColor" opacity="0.55"/>
            </svg>
          </button>
        </div>
        <div className="header-settings" ref={settingsRef}>
          <button
            className="icon-btn"
            onClick={() => setSettingsOpen((v) => !v)}
            title="Settings"
            aria-label="Open settings"
            aria-expanded={settingsOpen}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
              <path
                d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
                stroke="currentColor"
                strokeWidth="1.4"
              />
            </svg>
          </button>
          {settingsOpen && (
            <div className="settings-menu" role="menu">
              <div className="settings-menu-title">Theme</div>
              <button
                className={`settings-menu-item ${theme === 'light' ? 'on' : ''}`}
                role="menuitemradio"
                aria-checked={theme === 'light'}
                onClick={() => { setTheme('light'); setSettingsOpen(false); }}
              >
                Light
              </button>
              <button
                className={`settings-menu-item ${theme === 'dark' ? 'on' : ''}`}
                role="menuitemradio"
                aria-checked={theme === 'dark'}
                onClick={() => { setTheme('dark'); setSettingsOpen(false); }}
              >
                Dark
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
