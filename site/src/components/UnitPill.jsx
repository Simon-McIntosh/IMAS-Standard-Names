import { RichText } from './RichText.jsx';

export function UnitPill({ unit }) {
  if (!unit || unit === '1') {
    return <span className="unit-pill unitless">dimensionless</span>;
  }
  return (
    <span className="unit-pill">
      <RichText text={unit} />
    </span>
  );
}
