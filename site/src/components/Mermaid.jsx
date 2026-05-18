import { useEffect, useRef } from 'react';
import { ensureMermaidInit } from '../lib/mermaid.js';

// Mermaid renderer wrapper. The mermaid runtime (~1.5 MB) is loaded
// dynamically only when this component is actually mounted — no current
// view does so, but the component is here for future detail-section
// diagrams.
let mermaidCounter = 0;

export function Mermaid({ chart, theme = 'light' }) {
  const ref = useRef(null);
  useEffect(() => {
    let cancelled = false;
    if (!ref.current) return undefined;
    const id = `mmd-${++mermaidCounter}`;
    ensureMermaidInit(theme)
      .then((mermaid) => mermaid.render(id, chart))
      .then(({ svg }) => {
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      })
      .catch(() => {
        if (!cancelled && ref.current) ref.current.textContent = chart;
      });
    return () => {
      cancelled = true;
    };
  }, [chart, theme]);
  return <div ref={ref} className="mermaid-host" />;
}
