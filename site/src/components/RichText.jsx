import { MathInline } from './MathInline.jsx';

// Render a string with `$...$` inline math segments.
//
// Caveat: this regex does not handle escaped dollars (`\$`) or empty
// `$$` blocks. The dataset emitter must not produce literal `$` in
// `short`/`long`/`sign`/`unit`.
export function RichText({ text }) {
  if (!text) return null;
  const parts = [];
  const re = /\$([^$]+)\$/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) {
      parts.push(<span key={i++}>{text.slice(last, m.index)}</span>);
    }
    parts.push(<MathInline key={i++} tex={m[1]} />);
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    parts.push(<span key={i++}>{text.slice(last)}</span>);
  }
  return <>{parts}</>;
}
