import { useData } from '../lib/data.js';
import { clusterKey, clusterDescriptor } from '../lib/indexes.js';
import { NameCard } from './NameCard.jsx';

// Card-grid showing the local graph around a single name: parent,
// "this name", cluster mates (same locus / same base / same concept),
// children (names whose parent === n.name), and cross-reference chips.
export function NeighborhoodGraph({ n, onSelect, childIndex, groupIndex }) {
  const { NAMES } = useData();

  const parent = n.parent
    ? NAMES.find((x) => x.name === n.parent) ?? null
    : null;

  const myCluster = groupIndex[clusterKey(n)] || [];
  const clusterMembers = myCluster.filter((x) => x.name !== n.name);
  const descriptor = clusterDescriptor(myCluster, NAMES);

  const children = (childIndex[n.name] || []).filter(
    (c) => !clusterMembers.some((s) => s.name === c.name),
  );

  const seeAlso = (n.seeAlso || [])
    .map((s) => NAMES.find((x) => x.name === s))
    .filter((s) => s != null)
    .filter(
      (s) =>
        s.name !== parent?.name &&
        !clusterMembers.some((x) => x.name === s.name) &&
        !children.some((x) => x.name === s.name),
    );

  const parentEdge = n.axis
    ? `axis = ${n.axis}`
    : n.locus
    ? `evaluated at ${n.locus}`
    : 'is-a';

  let clusterTitle;
  let clusterSubtitle;
  if (descriptor.kind === 'locus') {
    clusterTitle = 'At the same locus';
    clusterSubtitle = (
      <>quantities evaluated at <span className="mono">{descriptor.root}</span></>
    );
  } else if (descriptor.kind === 'base') {
    clusterTitle = 'Same base quantity';
    clusterSubtitle = (
      <>components and variants of <span className="mono">{descriptor.root}</span></>
    );
  } else {
    clusterTitle = 'Same concept';
    clusterSubtitle = <>group <span className="mono">{descriptor.root}</span></>;
  }

  if (
    !parent &&
    clusterMembers.length === 0 &&
    children.length === 0 &&
    seeAlso.length === 0
  ) {
    return (
      <div className="nb-empty">
        This name has no recorded parents, related names, derived names, or references in the catalog.
      </div>
    );
  }

  return (
    <div className="nb">
      {parent && (
        <div className="nb-row nb-row-parent">
          <div className="nb-row-head">
            <span className="nb-row-label">Parent</span>
            <span className="nb-row-edge mono">{parentEdge}</span>
          </div>
          <div className="nb-cards">
            <NameCard n={parent} onSelect={onSelect} relation="parent" />
          </div>
        </div>
      )}

      <div className="nb-row nb-row-self">
        <div className="nb-row-head">
          <span className="nb-row-label">This name</span>
        </div>
        <div className="nb-cards">
          <NameCard n={n} relation="self" />
        </div>
      </div>

      {clusterMembers.length > 0 && (
        <div className="nb-row">
          <div className="nb-row-head">
            <span className="nb-row-label">{clusterTitle}</span>
            <span className="nb-row-count">
              {clusterMembers.length} other · {clusterSubtitle}
            </span>
          </div>
          <div className="nb-cards nb-cards-grid">
            {clusterMembers.map((s) => (
              <NameCard
                key={s.name}
                n={s}
                onSelect={onSelect}
                relation="sibling"
                edgeLabel={
                  s.axis
                    ? `axis = ${s.axis}`
                    : s.locus && s.locus !== descriptor.root
                    ? `at ${s.locus}`
                    : null
                }
              />
            ))}
          </div>
        </div>
      )}

      {children.length > 0 && (
        <div className="nb-row">
          <div className="nb-row-head">
            <span className="nb-row-label">Derived from this</span>
            <span className="nb-row-count">
              {children.length} {children.length === 1 ? 'name' : 'names'}
            </span>
          </div>
          <div className="nb-cards nb-cards-grid">
            {children.map((c) => (
              <NameCard
                key={c.name}
                n={c}
                onSelect={onSelect}
                relation="child"
                edgeLabel={
                  c.axis
                    ? `axis = ${c.axis}`
                    : c.locus
                    ? `at ${c.locus}`
                    : null
                }
              />
            ))}
          </div>
        </div>
      )}

      {seeAlso.length > 0 && (
        <div className="nb-row">
          <div className="nb-row-head">
            <span className="nb-row-label">References</span>
            <span className="nb-row-count">cross-links from description</span>
          </div>
          <div className="nb-cards nb-cards-grid">
            {seeAlso.map((s) => (
              <NameCard key={s.name} n={s} onSelect={onSelect} relation="ref" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
