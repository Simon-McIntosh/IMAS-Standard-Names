import { useEffect, useRef, useState } from 'react';

// Dev-only design tweaks panel. Gated behind `?tweaks=1` by App.jsx and
// lazy-loaded so it never lands in the default bundle.
//
// Strips the prototype's host-postMessage protocol — persistence is via
// localStorage through useTweaks(). Strips the deck-stage rail toggle.
// Otherwise the visual panel is the same set of controls as the
// prototype: density, theme mode, accent colour.

const PANEL_STYLE = `
  .twk-panel{position:fixed;right:16px;bottom:16px;z-index:2147483646;width:280px;
    max-height:calc(100vh - 32px);display:flex;flex-direction:column;
    background:rgba(250,249,247,.88);color:#29261b;
    -webkit-backdrop-filter:blur(24px) saturate(160%);backdrop-filter:blur(24px) saturate(160%);
    border:.5px solid rgba(255,255,255,.6);border-radius:14px;
    box-shadow:0 1px 0 rgba(255,255,255,.5) inset,0 12px 40px rgba(0,0,0,.18);
    font:11.5px/1.4 ui-sans-serif,system-ui,-apple-system,sans-serif;overflow:hidden}
  .twk-hd{display:flex;align-items:center;justify-content:space-between;
    padding:10px 8px 10px 14px;user-select:none}
  .twk-hd b{font-size:12px;font-weight:600;letter-spacing:.01em}
  .twk-x{appearance:none;border:0;background:transparent;color:rgba(41,38,27,.55);
    width:22px;height:22px;border-radius:6px;cursor:pointer;font-size:13px;line-height:1}
  .twk-x:hover{background:rgba(0,0,0,.06);color:#29261b}
  .twk-body{padding:2px 14px 14px;display:flex;flex-direction:column;gap:10px;
    overflow-y:auto;min-height:0}
  .twk-sect{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
    color:rgba(41,38,27,.45);padding:10px 0 0}
  .twk-sect:first-child{padding-top:0}
  .twk-row{display:flex;flex-direction:column;gap:5px}
  .twk-row-h{flex-direction:row;align-items:center;justify-content:space-between;gap:10px}
  .twk-lbl{display:flex;justify-content:space-between;align-items:baseline;
    color:rgba(41,38,27,.72)}
  .twk-lbl>span:first-child{font-weight:500}
  .twk-seg{position:relative;display:flex;padding:2px;border-radius:8px;
    background:rgba(0,0,0,.06);user-select:none}
  .twk-seg button{appearance:none;position:relative;z-index:1;flex:1;border:0;
    background:transparent;color:inherit;font:inherit;font-weight:500;min-height:22px;
    border-radius:6px;cursor:pointer;padding:4px 6px;line-height:1.2}
  .twk-seg button.on{background:rgba(255,255,255,.9);box-shadow:0 1px 2px rgba(0,0,0,.12)}
  .twk-chips{display:flex;gap:6px}
  .twk-chip{position:relative;appearance:none;flex:1;min-width:0;height:46px;
    padding:0;border:0;border-radius:6px;overflow:hidden;cursor:pointer;
    box-shadow:0 0 0 .5px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.06);
    transition:transform .12s cubic-bezier(.3,.7,.4,1),box-shadow .12s}
  .twk-chip:hover{transform:translateY(-1px)}
  .twk-chip[data-on="1"]{box-shadow:0 0 0 1.5px rgba(0,0,0,.85),0 2px 6px rgba(0,0,0,.15)}
`;

function TweakSection({ label, children }) {
  return (
    <>
      <div className="twk-sect">{label}</div>
      {children}
    </>
  );
}

function TweakRadio({ label, value, options, onChange }) {
  const opts = options.map((o) => (typeof o === 'object' ? o : { value: o, label: o }));
  return (
    <div className="twk-row">
      <div className="twk-lbl">
        <span>{label}</span>
      </div>
      <div className="twk-seg" role="radiogroup">
        {opts.map((o) => (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={o.value === value}
            className={o.value === value ? 'on' : ''}
            onClick={() => onChange(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function TweakColor({ label, value, options, onChange }) {
  return (
    <div className="twk-row">
      <div className="twk-lbl"><span>{label}</span></div>
      <div className="twk-chips" role="radiogroup">
        {options.map((c) => (
          <button
            key={c}
            type="button"
            role="radio"
            aria-checked={c === value}
            data-on={c === value ? '1' : '0'}
            className="twk-chip"
            style={{ background: c }}
            title={c}
            onClick={() => onChange(c)}
            aria-label={c}
          />
        ))}
      </div>
    </div>
  );
}

export default function DevTweaks({ tweaks, setTweak }) {
  const [open, setOpen] = useState(true);
  const panelRef = useRef(null);

  // Drag-to-move (right/bottom offsets) — same UX as the prototype but
  // without ResizeObserver / clampToViewport. Simpler is fine here.
  const [offset, setOffset] = useState({ x: 16, y: 16 });
  useEffect(() => {
    if (panelRef.current) {
      panelRef.current.style.right = offset.x + 'px';
      panelRef.current.style.bottom = offset.y + 'px';
    }
  }, [offset]);

  const onDragStart = (e) => {
    if (!panelRef.current) return;
    const r = panelRef.current.getBoundingClientRect();
    const sx = e.clientX;
    const sy = e.clientY;
    const startRight = window.innerWidth - r.right;
    const startBottom = window.innerHeight - r.bottom;
    const move = (ev) => {
      setOffset({
        x: Math.max(8, startRight - (ev.clientX - sx)),
        y: Math.max(8, startBottom - (ev.clientY - sy)),
      });
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  if (!open) return null;

  return (
    <>
      <style>{PANEL_STYLE}</style>
      <div ref={panelRef} className="twk-panel">
        <div className="twk-hd" onMouseDown={onDragStart} style={{ cursor: 'move' }}>
          <b>Tweaks</b>
          <button className="twk-x" onClick={() => setOpen(false)}>✕</button>
        </div>
        <div className="twk-body">
          <TweakSection label="Density">
            <TweakRadio
              label="List rows"
              value={tweaks.density}
              options={[
                { value: 'comfortable', label: 'Comfy' },
                { value: 'compact', label: 'Compact' },
                { value: 'dense', label: 'Dense' },
              ]}
              onChange={(v) => setTweak('density', v)}
            />
          </TweakSection>
          <TweakSection label="Layout">
            <TweakRadio
              label="Group results"
              value={tweaks.groupBy}
              options={[
                { value: 'none', label: 'A–Z' },
                { value: 'category', label: 'Domain' },
                { value: 'cluster', label: 'Concept' },
              ]}
              onChange={(v) => setTweak('groupBy', v)}
            />
          </TweakSection>
          <TweakSection label="Theme">
            <TweakRadio
              label="Mode"
              value={tweaks.theme}
              options={[
                { value: 'light', label: 'Light' },
                { value: 'dark', label: 'Dark' },
              ]}
              onChange={(v) => setTweak('theme', v)}
            />
            <TweakColor
              label="Accent"
              value={tweaks.accent}
              options={['#3654c8', '#0d7c66', '#a8430d', '#7a3aa8', '#1d2230']}
              onChange={(v) => setTweak('accent', v)}
            />
          </TweakSection>
        </div>
      </div>
    </>
  );
}
