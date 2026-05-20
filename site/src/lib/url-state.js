import { useState, useEffect } from 'react';

// Hash format: #/<view>/<encoded-name?>?q=<encoded-query>
//
// `replaceState` (not `pushState`) is used so each keystroke in the search
// box doesn't spam browser history.

export function parseHash() {
  const h = window.location.hash.replace(/^#\/?/, '');
  const [path, q = ''] = h.split('?');
  const [view = 'browse', name = ''] = path.split('/');
  const params = new URLSearchParams(q);
  return {
    view: view === 'matrix' ? 'matrix' : 'browse',
    name: name ? decodeURIComponent(name) : null,
    query: params.get('q') || '',
  };
}

export function writeHash({ view, name, query }) {
  let h = `#/${view}`;
  if (name) h += `/${encodeURIComponent(name)}`;
  if (query) h += `?q=${encodeURIComponent(query)}`;
  if (h !== window.location.hash) {
    history.replaceState(null, '', h);
  }
}

export function useUrlState() {
  const [state, setState] = useState(() => parseHash());
  useEffect(() => {
    const onHashChange = () => setState(parseHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  useEffect(() => {
    writeHash(state);
  }, [state]);
  return [state, setState];
}
