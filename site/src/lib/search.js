// Standard-name search.
//
// Token model:
//   * Whitespace-split the trimmed lowercase query.
//   * Each token must match SOMEWHERE in the row (AND across tokens) —
//     the previous OR'd-substring scan returned obvious false positives
//     ("pressure" matching `field_at_separatrix` via char-cluster overlap
//     after a too-permissive fuzzy threshold).
//   * For each token, the best-scoring per-field match contributes its
//     weight to the row total. Field weights are tuned so that a hit on
//     the canonical name dominates a hit on the description, and an
//     exact unit beats either.
//
// Per-token weights (highest wins):
//   8  name substring
//   6  exact unit (e.g. token === "pa" matches unit "Pa")
//   4  tag substring
//   3  alias substring (token expanded via ALIASES)
//   2  short description substring
//   1  long description substring
//
// Row score = Σ best per-token weight. If ANY token fails to hit in any
// field, the row is excluded (this is what makes the AND strict).
//
// Sort: descending score, then ascending name length (a shorter match
// is more specific than a longer one).

export const ALIASES = {
  pressure: ['pa', 'pressure'],
  field: ['t', 'field'],
  current: ['a', 'current'],
  flux: ['wb', 'flux'],
  density: ['m^-3', 'density'],
  energy: ['j', 'ev', 'energy'],
  temperature: ['ev', 't_e', 't_i', 'temperature'],
};

export function tokenize(query) {
  return (query || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
}

export function matchScore(name, tokens) {
  if (!tokens || tokens.length === 0) return null;
  let total = 0;
  for (const tok of tokens) {
    const w = bestFieldWeight(name, tok);
    if (w === 0) return null; // AND: every token must hit
    total += w;
  }
  return total;
}

function bestFieldWeight(name, tok) {
  const unit = (name.unit || '').toLowerCase();
  if (unit && tok === unit) return 6;
  if ((name.name || '').toLowerCase().includes(tok)) return 8;
  if (name.tags && name.tags.some((t) => (t || '').toLowerCase().includes(tok))) return 4;
  const aliasTargets = ALIASES[tok];
  if (
    aliasTargets &&
    aliasTargets.some(
      (a) =>
        (name.name || '').toLowerCase().includes(a) || a === unit,
    )
  ) {
    return 3;
  }
  if ((name.short || '').toLowerCase().includes(tok)) return 2;
  if ((name.long || '').toLowerCase().includes(tok)) return 1;
  return 0;
}

// Search the corpus and return scored rows sorted score-desc, then
// name-length-asc. `tokens` is what tokenize() returns; passing it in
// (rather than the raw query) lets callers display the parsed tokens
// in the empty state without re-tokenising.
export function searchNames(NAMES, tokens) {
  if (!tokens || tokens.length === 0) {
    return { mode: 'all', results: NAMES };
  }
  const scored = [];
  for (const n of NAMES) {
    const s = matchScore(n, tokens);
    if (s !== null) scored.push({ row: n, score: s });
  }
  if (scored.length === 0) {
    // Conservative fuzzy fallback: per-token, allow a non-contiguous
    // subsequence match against the canonical name only. Restricts the
    // surface area enough to avoid the original OR-fuzzy false positives.
    const fuzzy = [];
    for (const n of NAMES) {
      const ok = tokens.every(
        (t) => t.length >= 3 && containsSubsequence((n.name || '').toLowerCase(), t),
      );
      if (ok) fuzzy.push({ row: n, score: 0 });
    }
    if (fuzzy.length === 0) {
      return { mode: 'empty', results: [] };
    }
    return {
      mode: 'fuzzy',
      results: fuzzy
        .map(({ row }) => row)
        .sort((a, b) => a.name.length - b.name.length),
    };
  }
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.row.name.length - b.row.name.length;
  });
  return { mode: 'scored', results: scored.map(({ row }) => row) };
}

// Non-contiguous subsequence test: each character of `needle` must
// appear in `haystack` in order. Cheap; works for any string length.
function containsSubsequence(haystack, needle) {
  let i = 0;
  for (let j = 0; j < haystack.length && i < needle.length; j++) {
    if (haystack[j] === needle[i]) i++;
  }
  return i === needle.length;
}
