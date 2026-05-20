import { KindBadge } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';

// One card inside the neighborhood graph. `relation` controls the
// left-border colour via `.nb-card-${relation}` rules in styles.css.
export function NameCard({ n, onSelect, relation, edgeLabel }) {
  const isSelf = relation === 'self';
  const missing = n.missing;
  return (
    <button
      className={`nb-card nb-card-${relation} ${missing ? 'missing' : ''}`}
      onClick={() => !isSelf && !missing && onSelect && onSelect(n.name)}
      disabled={isSelf || missing}
      title={missing ? 'Not yet in catalog' : n.short}
    >
      <div className="nb-card-top">
        {(n.kind || n.algebra) && (
          <KindBadge name={n} />
        )}
        <span className="nb-card-name mono">{n.name}</span>
        {n.unit && <UnitPill unit={n.unit} />}
      </div>
      {n.short && <div className="nb-card-desc">{n.short}</div>}
      {edgeLabel && <div className="nb-card-edge mono">{edgeLabel}</div>}
    </button>
  );
}
