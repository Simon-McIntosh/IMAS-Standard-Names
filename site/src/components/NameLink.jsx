import { useData } from '../lib/data.js';

// Inline cross-reference link to another standard name. Renders as a
// <span role="link"> rather than a <button> so the element stays
// `display: inline` and flows with surrounding prose — buttons force
// inline-block, which breaks text reflow and leaves stacked boxes when
// the link wraps across a line.
//
// Visual rules:
//   - Link text is the humanised name ("plasma_current" → "plasma current").
//   - Kind glyph and unit pill never appear inline — they live in the
//     native title tooltip only.
//   - Missing targets render with `.name-link.missing`, no click handler,
//     cursor: help. The tooltip still surfaces the canonical name.
//
// Interaction:
//   - Click invokes onSelect(name).
//   - Enter / Space invoke onSelect(name) too (keyboard accessibility).
export function NameLink({ name, label, onSelect }) {
  const { NAMES } = useData();
  const n = NAMES.find((x) => x.name === name);
  const exists = !!n;
  const display = label || humanize(name);
  const unit = exists && n.unit ? n.unit : 'dimensionless';
  const short = exists && n.short ? n.short : 'Not yet in catalog';
  const title = `${name}  ·  [${unit}]  ${short}`;

  if (!exists) {
    return (
      <span
        className="name-link missing"
        data-name={name}
        title={`${name}  ·  Not yet in catalog`}
      >
        {display}
      </span>
    );
  }

  const fire = () => onSelect && onSelect(name);
  const onKey = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fire();
    }
  };

  return (
    <span
      className="name-link"
      role="link"
      tabIndex={0}
      data-name={name}
      title={title}
      onClick={fire}
      onKeyDown={onKey}
    >
      {display}
    </span>
  );
}

function humanize(name) {
  return name.replace(/_/g, ' ');
}
