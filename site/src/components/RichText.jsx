import { MathInline, MathDisplay } from './MathInline.jsx';
import { NameLink } from './NameLink.jsx';

// Render a string with markdown-lite formatting.
//
// Supported constructs (matching the dataset emitter's output):
//
//   - `$$ ... $$`           → display math block (KaTeX)
//   - `$ ... $`             → inline math span (KaTeX)
//   - `[label](name:foo)`   → cross-catalog link rendered as <NameLink>,
//                             an inline span (NOT a button) so prose reflows
//                             cleanly across line breaks.
//   - blank lines           → paragraph break
//
// Two render modes:
//
//   - block (default)       → wraps each paragraph in <p>, emits
//                             <MathDisplay> as a sibling block when a
//                             paragraph is a standalone `$$...$$`.
//                             Use for `long` / `sign` / multi-paragraph text.
//   - inline                → never emits <p> or block-level math;
//                             everything is rendered as inline spans.
//                             Use for short labels (units, single-line
//                             descriptions) embedded in other elements.
export function RichText({ text, onSelect, inline = false }) {
  if (!text) return null;

  if (inline) {
    // Strip paragraph breaks; render the whole string as a single
    // inline tokenized stream. Display math degrades to inline math
    // because we cannot emit a <div> in an inline context.
    return <>{renderInline(text.replace(/\s*\n+\s*/g, ' '), onSelect, 'i')}</>;
  }

  const paragraphs = splitParagraphs(text);
  return (
    <>
      {paragraphs.map((para, pi) => {
        const displayOnly = matchSoleDisplayMath(para);
        if (displayOnly !== null) {
          return <MathDisplay key={pi} tex={displayOnly} />;
        }
        return (
          <p key={pi} className="rt-p">
            {renderInline(para, onSelect, pi)}
          </p>
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function splitParagraphs(text) {
  return text
    .split(/\n[ \t]*\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

function matchSoleDisplayMath(para) {
  const m = /^\$\$([\s\S]+?)\$\$\s*$/.exec(para);
  if (!m) return null;
  return m[1].trim();
}

function renderInline(text, onSelect, paraKey) {
  const tokens = tokenize(text);
  const out = [];
  tokens.forEach((tok, i) => {
    const key = `${paraKey}-${i}`;
    switch (tok.type) {
      case 'inline-math':
      case 'display-math':
        // Inside flow text we always use inline math; standalone
        // display math is handled one level up in RichText.
        out.push(<MathInline key={key} tex={tok.value} />);
        break;
      case 'name-link':
        out.push(
          <NameLink
            key={key}
            name={tok.value}
            label={tok.label}
            onSelect={onSelect || (() => {})}
          />,
        );
        break;
      default:
        out.push(<span key={key}>{tok.value}</span>);
    }
  });
  return out;
}

const TOKEN_RE = new RegExp(
  [
    '\\$\\$([\\s\\S]+?)\\$\\$', // group 1: display math
    '\\$([^$]+?)\\$', // group 2: inline math
    '\\[([^\\]]+)\\]\\(name:([a-z0-9_]+)\\)', // groups 3, 4: link label + target
  ].join('|'),
  'g',
);

function tokenize(text) {
  const out = [];
  let cursor = 0;
  let m;
  TOKEN_RE.lastIndex = 0;
  while ((m = TOKEN_RE.exec(text))) {
    if (m.index > cursor) {
      out.push({ type: 'text', value: text.slice(cursor, m.index) });
    }
    if (m[1] !== undefined) {
      out.push({ type: 'display-math', value: m[1].trim() });
    } else if (m[2] !== undefined) {
      out.push({ type: 'inline-math', value: m[2].trim() });
    } else if (m[4] !== undefined) {
      out.push({ type: 'name-link', value: m[4], label: m[3] });
    }
    cursor = m.index + m[0].length;
  }
  if (cursor < text.length) {
    out.push({ type: 'text', value: text.slice(cursor) });
  }
  return out;
}
