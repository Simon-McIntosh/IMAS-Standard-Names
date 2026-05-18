import { useEffect, useRef } from 'react';
import katex from 'katex';
import { KATEX_OPTS } from '../lib/katex.js';

// Inline KaTeX math span. Errors are swallowed silently per
// `throwOnError: false`; on render failure we drop back to the raw TeX
// so the page never blanks because of a malformed expression.
export function MathInline({ tex }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    try {
      katex.render(tex, ref.current, { ...KATEX_OPTS, displayMode: false });
    } catch {
      ref.current.textContent = tex;
    }
  }, [tex]);
  return <span ref={ref} className="katex-host" />;
}
