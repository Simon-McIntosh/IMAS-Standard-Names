import { useEffect, useRef, useState } from 'react';

// Styled inline version selector that reads mike's versions.json.
// Renders as an inline text button that expands into a dropdown overlay.
// Falls back to nothing when no versions are available.
export function VersionSwitcher({ versions, current, onSelect }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Close on outside click or Escape.
  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const esc = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);

  if (!versions || versions.length === 0) return null;

  const currentEntry = versions.find((v) => v.version === current);
  const label = currentEntry
    ? (currentEntry.aliases?.includes('latest')
      ? `${currentEntry.version} (latest)`
      : currentEntry.version)
    : current || 'unknown';

  return (
    <span className="ver-sel" ref={ref}>
      <button
        className="ver-sel-btn"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        title="Switch catalog version"
      >
        {label}
        <svg className="ver-sel-chevron" width="8" height="8" viewBox="0 0 8 8">
          <path d="M1.5 3L4 5.5L6.5 3" stroke="currentColor" strokeWidth="1.2"
                fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <ul className="ver-sel-menu" role="listbox">
          {versions.map((v) => (
            <li
              key={v.version}
              role="option"
              aria-selected={v.version === current}
              className={`ver-sel-item${v.version === current ? ' active' : ''}`}
              onClick={() => { onSelect(v); setOpen(false); }}
            >
              <span className="ver-sel-item-name">{v.version}</span>
              {v.aliases?.length > 0 && (
                <span className="ver-sel-item-alias">{v.aliases.join(', ')}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </span>
  );
}
