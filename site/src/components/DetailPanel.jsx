import { useEffect, useRef } from 'react';
import { useData } from '../lib/data.js';
import { groupSources } from '../lib/indexes.js';
import { KindBadge } from './KindBadge.jsx';
import { UnitPill } from './UnitPill.jsx';
import { RichText } from './RichText.jsx';
import { ParseBreakdown } from './ParseBreakdown.jsx';
import { NeighborhoodGraph } from './NeighborhoodGraph.jsx';
import { NameLink } from './NameLink.jsx';
import { SourceGroup } from './SourceGroup.jsx';

// Right pane: the definition of a single name.
export function DetailPanel({
  name, onSelect, onClose, childIndex, groupIndex,
  filters, setFilters, setView, dense,
}) {
  const { NAMES, CATEGORIES } = useData();
  const n = NAMES.find((x) => x.name === name);

  const scrollRef = useRef(null);
  const heroRef = useRef(null);
  useEffect(() => {
    const root = scrollRef.current;
    const hero = heroRef.current;
    if (!root || !hero) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        root.classList.toggle('detail-scrolled', !entry.isIntersecting);
      },
      { root, threshold: 0, rootMargin: '-8px 0px 0px 0px' },
    );
    obs.observe(hero);
    return () => obs.disconnect();
  }, [name]);

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
    <div className="detail" ref={scrollRef}>
      <div className="detail-sticky" aria-hidden="false">
        <KindBadge name={n} />
        <span className="detail-sticky-name mono">{n.name}</span>
        <UnitPill unit={n.unit} />
        <button className="icon-btn detail-sticky-close" onClick={onClose} title="Close">✕</button>
      </div>
      <div className="detail-top">
        <div className="detail-breadcrumb">
          <span>{cat?.label}</span>
          <span className="bc-sep">›</span>
          <span>{n.group}</span>
        </div>
        <button className="icon-btn" onClick={onClose} title="Close">✕</button>
      </div>

      <div className="detail-hero" ref={heroRef}>
        <KindBadge name={n} />
        <h1 className="detail-name">{n.name}</h1>
        <UnitPill unit={n.unit} />
      </div>

      {n.status && n.status !== 'active' && (() => {
        const LABEL = {
          draft: 'Draft',
          deprecated: 'Deprecated',
          superseded: 'Superseded',
        };
        const SUBTITLE = {
          draft: ' · proposed name under review, not yet ratified',
          deprecated: ' · scheduled for removal, no replacement',
          superseded: null,
        };
        return (
          <div className={`detail-lifecycle-banner state-${n.status}`} role="status">
            <span className="banner-glyph" aria-hidden="true">
              {n.status === 'draft' ? '✎' : '⚠'}
            </span>
            <div className="banner-body">
              <strong>{LABEL[n.status] || n.status}</strong>
              {n.status === 'superseded' && n.superseded_by && (
                <>
                  {' · superseded by '}
                  <NameLink name={n.superseded_by} onSelect={onSelect} />
                </>
              )}
              {SUBTITLE[n.status] && (
                <span className="banner-subtle">{SUBTITLE[n.status]}</span>
              )}
            </div>
          </div>
        );
      })()}

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
          <button
            className="detail-h-link"
            onClick={() => setView && setView('grammar')}
            title={`Open ${n.name} in the Grammar composer`}
          >
            Grammar
            <svg className="jump-arrow" width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M5 11L11 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              <path d="M6 5h5v5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <span className="detail-h-sub">canonical decomposition into tokens</span>
        </h3>
        <ParseBreakdown
          name={n.name}
          parse={n.parse}
          filters={filters}
          setFilters={setFilters}
        />
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
          dense={dense}
        />
      </section>

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
