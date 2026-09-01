// Mermaid initialiser.
//
// Mermaid is ~1.5 MB minified and no current view in the SPA actually
// renders Mermaid diagrams (the Map view is hand-coded SVG), so we lazy
// load mermaid only when `<Mermaid/>` is first mounted. To support that,
// this module never imports `mermaid` at the top level; the dynamic
// import lives inside the component. `initMermaidTheme` is the
// re-initialisation hook called whenever the user toggles the theme.

let mermaidPromise = null;

export function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid').then((m) => m.default);
  }
  return mermaidPromise;
}

function makeOptions(theme) {
  return {
    startOnLoad: false,
    theme: theme === 'dark' ? 'dark' : 'neutral',
    themeVariables: { fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' },
    flowchart: { curve: 'basis', padding: 12 },
    securityLevel: 'loose',
  };
}

let initialised = false;

// Called from App's theme effect. We only do real work after the user
// has actually exercised <Mermaid/> at least once (i.e. mermaid has been
// imported); otherwise this is a cheap no-op.
export function setMermaidTheme(theme) {
  if (!mermaidPromise) return;
  mermaidPromise.then((mermaid) => {
    mermaid.initialize(makeOptions(theme));
    initialised = true;
  });
}

// Called from <Mermaid/> on mount with the current theme.
export async function ensureMermaidInit(theme) {
  const mermaid = await loadMermaid();
  if (!initialised) {
    mermaid.initialize(makeOptions(theme));
    initialised = true;
  }
  return mermaid;
}
