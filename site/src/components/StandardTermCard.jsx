export function StandardTermCard({ term, examples = [], onClose }) {
  if (!term) return null;
  return (
    <aside className="term-card" id={`term-${term.token}`} aria-label={`Definition of ${term.token}`}>
      {onClose && <button className="term-card-close" onClick={onClose} aria-label="Close term definition">×</button>}
      <div className="term-card-segment">{term.segment}</div>
      <h4 className="mono">{term.token}</h4>
      {term.abbreviations?.length > 0 && <div className="term-card-abbr">Also displayed as {term.abbreviations.join(', ')}</div>}
      <p>{term.definition}</p>
      {term.allowed_relations?.length > 0 && (
        <div className="term-card-rel">Relations: {term.allowed_relations.map((r) => <code key={r}>{r}</code>)}</div>
      )}
      {examples.length > 0 && (
        <div className="term-card-examples"><strong>Catalog examples</strong>{examples.slice(0, 5).map((name) => <code key={name}>{name}</code>)}</div>
      )}
      <a href={`#/grammar?term=${encodeURIComponent(term.token)}`} className="term-card-share">Share this term ↗</a>
    </aside>
  );
}
