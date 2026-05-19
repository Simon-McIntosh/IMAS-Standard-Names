import { useData } from '../lib/data.js';
import { groupSources } from '../lib/indexes.js';
import { KindBadge, KIND_GLYPHS, ALGEBRA_CHIPS } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';
import { RichText } from './RichText.jsx';
import { ParseBreakdown } from './ParseBreakdown.jsx';
import { NeighborhoodGraph } from './NeighborhoodGraph.jsx';
import { NameLink } from './NameLink.jsx';
import { SourceGroup } from './SourceGroup.jsx';

// Right pane: the definition of a single name.
export function DetailPanel({ name, onSelect, onClose, childIndex, groupIndex }) {
  const { NAMES, CATEGORIES } = useData();
  const n = NAMES.find((x) => x.name === name);

  if (!n) {
    return (
      <div className="detail-empty">
        <div className="detail-empty-glyph">←</div>
        <div className="detail-empty-text">Select a name to see its definition.</div>
        <div className="detail-empty-hint">Use ⌘K to search · ↑↓ to navigate</div>
      </div>
    );
  }

  const grouped = groupSources(n.sources);
  const cat = CATEGORIES.find((c) => c.id === n.category);
  const sourceWord = n.sources.length === 1 ? 'path' : 'paths';

  return (
    <div className="detail">
      <div className="detail-top">
        <div className="detail-breadcrumb">
          <span>{cat?.label}</span>
          <span className="bc-sep">›</span>
          <span>{n.group}</span>
        </div>
        <button className="icon-btn" onClick={onClose} title="Close">✕</button>
      </div>

      <div className="detail-hero">
        <KindBadge kind={n.display_kind ?? n.kind} algebra={n.algebra} />
        <h1 className="detail-name">{n.name}</h1>
        {n.status && n.status !== 'drafted' && n.status !== 'draft' && (
          <span className={`status-pill status-${n.status}`}>{n.status}</span>
        )}
      </div>

      <div className="detail-attrs">
        <div className="attr">
          <div className="attr-k">Unit</div>
          <div className="attr-v"><UnitPill unit={n.unit} /></div>
        </div>
        <div className="attr">
          <div className="attr-k">Algebra</div>
          <div className="attr-v">
            {ALGEBRA_CHIPS[n.algebra]?.title ?? n.algebra ?? '—'}
          </div>
        </div>
        <div className="attr">
          <div className="attr-k">Shape</div>
          <div className="attr-v">
            {KIND_GLYPHS[n.display_kind ?? n.kind]?.title ?? '—'}
          </div>
        </div>
        {n.subject && (
          <div className="attr">
            <div className="attr-k">Subject</div>
            <div className="attr-v mono">{n.subject}</div>
          </div>
        )}
        {n.locus && (
          <div className="attr">
            <div className="attr-k">At locus</div>
            <div className="attr-v mono">{n.locus}</div>
          </div>
        )}
        {n.axis && (
          <div className="attr">
            <div className="attr-k">Axis</div>
            <div className="attr-v mono">{n.axis}</div>
          </div>
        )}
        <div className="attr">
          <div className="attr-k">Sources</div>
          <div className="attr-v">
            {n.sources.length} data dictionary {sourceWord}
          </div>
        </div>
      </div>

      {n.algebra === 'vector' && (n.components?.length > 0 || n.magnitude) && (
        <section className="detail-section detail-algebra">
          <h3 className="detail-h">
            Algebra
            <span className="detail-h-sub">vector components and magnitude</span>
          </h3>
          {n.components?.length > 0 && (
            <div className="detail-components">
              <div className="detail-components-k">Components</div>
              <div className="detail-components-v">
                {n.components.map((c, i) => (
                  <span key={c.name} className="detail-component">
                    {i > 0 && <span className="component-sep">·</span>}
                    <span className="component-axis mono">{c.axis}</span>
                    <NameLink name={c.name} onSelect={onSelect} />
                  </span>
                ))}
              </div>
            </div>
          )}
          {n.magnitude && (
            <div className="detail-components">
              <div className="detail-components-k">Magnitude</div>
              <div className="detail-components-v">
                <NameLink name={n.magnitude} onSelect={onSelect} />
              </div>
            </div>
          )}
        </section>
      )}

      <section className="detail-section detail-short">
        <RichText text={n.short} onSelect={onSelect} inline />
      </section>

      <section className="detail-section">
        <h3 className="detail-h">Description</h3>
        <div className="detail-long">
          <RichText text={n.long} onSelect={onSelect} />
        </div>
      </section>

      {n.sign && (
        <section className="detail-section">
          <h3 className="detail-h">Sign convention</h3>
          <div className="detail-sign">
            <RichText text={n.sign} onSelect={onSelect} />
          </div>
        </section>
      )}

      <section className="detail-section">
        <h3 className="detail-h">
          Grammar
          <span className="detail-h-sub">canonical decomposition into tokens</span>
        </h3>
        <ParseBreakdown name={n.name} parse={n.parse} onSelect={onSelect} />
      </section>

      <section className="detail-section">
        <h3 className="detail-h">
          Neighborhood
          <span className="detail-h-sub">parents · siblings · children · references</span>
        </h3>
        <NeighborhoodGraph
          n={n}
          onSelect={onSelect}
          childIndex={childIndex}
          groupIndex={groupIndex}
        />
      </section>

      {n.seeAlso?.length > 0 && (
        <section className="detail-section">
          <h3 className="detail-h">See also</h3>
          <div className="see-also">
            {n.seeAlso.map((s, i) => (
              <span key={s} className="see-also-item">
                {i > 0 && <span className="see-also-sep">·</span>}
                <NameLink name={s} onSelect={onSelect} />
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="detail-section">
        <h3 className="detail-h">
          Sources
          <span className="detail-h-sub">
            {n.sources.length} data-dictionary {sourceWord}
          </span>
        </h3>
        <div className="sources">
          {grouped.map(([ids, items]) => (
            <SourceGroup key={ids} ids={ids} items={items} />
          ))}
        </div>
      </section>
    </div>
  );
}
