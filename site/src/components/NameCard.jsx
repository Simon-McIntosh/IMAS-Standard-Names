import { KindBadge } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';

// One card inside the neighborhood graph. `relation` controls the
// left-border colour via `.nb-card-${relation}` rules in styles.css.
// `dense` mirrors the main list density selector ('comfortable' | 'compact' | 'dense').
export function NameCard({ n, onSelect, relation, edgeLabel, dense }) {
  const isSelf = relation === 'self';
  const missing = n.missing;
  const d = dense || 'comfortable';
  return (
    <button
      className={`nb-card nb-card-${relation} dense-${d} ${missing ? 'missing' : ''}`}
      onClick={() => !isSelf && !missing && onSelect && onSelect(n.name)}
      disabled={isSelf || missing}
      title={missing ? 'Not yet in catalog' : n.short}
    >
      <div className="nb-card-top">
        {d !== 'dense' && n.algebra && <KindBadge name={n} />}
        <span className="nb-card-name mono">{n.name}</span>
        {d !== 'dense' && n.unit && <UnitPill unit={n.unit} />}
      </div>
      {d !== 'dense' && n.short && <div className="nb-card-desc">{n.short}</div>}
      {d === 'comfortable' && edgeLabel && <div className="nb-card-edge mono">{edgeLabel}</div>}
    </button>
  );
}
