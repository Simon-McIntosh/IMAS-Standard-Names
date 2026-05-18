import { useData } from '../lib/data.js';
import { KindBadge } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';

// Linked name reference. Renders enabled with kind+unit when the target
// exists in NAMES; renders dashed/disabled with a "Not yet in catalog"
// tooltip otherwise.
export function NameChip({ name, onSelect, kind = 'ref' }) {
  const { NAMES } = useData();
  const n = NAMES.find((x) => x.name === name);
  const exists = !!n;
  return (
    <button
      className={`name-chip ${exists ? '' : 'missing'} chip-${kind}`}
      onClick={() => exists && onSelect(name)}
      title={exists ? n.short : 'Not yet in catalog'}
    >
      {exists && n.kind && <KindBadge kind={n.kind} />}
      <span className="mono">{name}</span>
      {exists && <UnitPill unit={n.unit} />}
    </button>
  );
}
