import { useMemo } from 'react';
import { cmpOrderKey } from './data.js';

// Cluster key combines category + group so locus clusters from different
// categories (e.g. two "magnetic axis" groups) stay distinct.
export function clusterKey(n) {
  return `${n.category}::${n.group}`;
}

// Pretty cluster name + a structural root description.
//
// A cluster of at-point names rolls up to its locus; a cluster of
// components rolls up to its parent base; otherwise we fall back to the
// group label.
export function clusterDescriptor(members, allNames) {
  const loci = new Set(
    members.filter((m) => m.kind === 'at_point' && m.locus).map((m) => m.locus),
  );
  if (loci.size === 1) {
    const locus = [...loci][0];
    const real = allNames.some((n) => n.name === locus);
    return { root: locus, kind: 'locus', real };
  }
  const parents = new Set(members.filter((m) => m.parent).map((m) => m.parent));
  if (parents.size === 1) {
    const p = [...parents][0];
    const real = allNames.some((n) => n.name === p);
    return { root: p, kind: 'base', real };
  }
  return { root: members[0]?.group || '?', kind: 'concept', real: false };
}

// Build the parent → children index. Memoised because all NAMES are scanned.
// Children are sorted by `cmpOrderKey` so consumers never need to re-sort.
export function useChildIndex(names) {
  return useMemo(() => {
    const idx = {};
    for (const n of names) {
      if (n.parent) (idx[n.parent] ||= []).push(n);
    }
    for (const k in idx) idx[k].sort(cmpOrderKey);
    return idx;
  }, [names]);
}

// Build the cluster-key → sorted member list index.
export function useGroupIndex(names) {
  return useMemo(() => {
    const idx = {};
    for (const n of names) {
      const k = clusterKey(n);
      (idx[k] ||= []).push(n);
    }
    for (const k in idx) idx[k].sort(cmpOrderKey);
    return idx;
  }, [names]);
}

// Group a list of sources by their IDS root (path segment before the first '/').
// Returned entries are sorted descending by member count so the biggest IDS
// group renders first in the detail panel.
export function groupSources(sources) {
  const by = {};
  for (const s of sources) {
    const root = s.path.split('/')[0];
    (by[root] ||= []).push(s);
  }
  return Object.entries(by).sort((a, b) => b[1].length - a[1].length);
}
