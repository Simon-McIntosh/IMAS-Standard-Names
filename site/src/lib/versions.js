// Numeric ordering for mike's versions.json entries.
//
// mike writes version directories in whatever order the filesystem or his
// own build script produced them — effectively lexicographic string order.
// That sorts 'v0.2.0rc9' above 'v0.2.0rc63' (string '9' > '6'), which is
// wrong for a release-candidate sequence. This module parses each version
// string into (major, minor, patch, rc) and compares numerically, newest
// first, with a stable release sorting above all its own release
// candidates.
//
// Semver build metadata (`+west-task-2e`, dot-separated [0-9A-Za-z-]
// identifiers) is parsed off but carries NO precedence weight — per the
// semver spec, `v0.2.0rc65+a` and `v0.2.0rc65+b` and `v0.2.0rc65` all tie.
// Ties are broken by the stable underlying sort (Array#sort with a
// comparator returning 0 preserves input order), so same-precedence
// entries never shuffle between deploys. The build metadata is never
// stripped from the entry itself — only `version` strings are parsed for
// comparison; the caller's objects (and their `title`/`aliases`) pass
// through untouched.

const VERSION_RE = /^v?(\d+)\.(\d+)\.(\d+)(?:-?rc(\d+))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/i;

/**
 * Parse a version string into its numeric components.
 * Returns null when the string does not match the expected shape.
 *
 * @param {string} version
 * @returns {{ major: number, minor: number, patch: number, rc: number|null } | null}
 */
export function parseVersion(version) {
  const m = VERSION_RE.exec(String(version ?? '').trim());
  if (!m) return null;
  const [, major, minor, patch, rc] = m;
  return {
    major: Number(major),
    minor: Number(minor),
    patch: Number(patch),
    // No rc suffix means a stable release — represented as null so it can
    // be ordered above any rc of the same major.minor.patch.
    rc: rc === undefined ? null : Number(rc),
  };
}

/**
 * Compare two parsed versions, descending (newest first). A stable release
 * (rc === null) sorts above every rc of the same major.minor.patch. Build
 * metadata is not part of the parsed shape (it carries no precedence), so
 * two entries differing only by build metadata compare equal (0) and their
 * relative order is left to the caller's stable sort.
 *
 * @param {{major:number,minor:number,patch:number,rc:number|null}} a
 * @param {{major:number,minor:number,patch:number,rc:number|null}} b
 */
function compareParsed(a, b) {
  if (a.major !== b.major) return b.major - a.major;
  if (a.minor !== b.minor) return b.minor - a.minor;
  if (a.patch !== b.patch) return b.patch - a.patch;
  if (a.rc === b.rc) return 0;
  if (a.rc === null) return -1; // stable outranks any rc
  if (b.rc === null) return 1;
  return b.rc - a.rc;
}

/**
 * Sort a list of version entries newest-first by numeric semver + rc.
 * Accepts either `{version, ...}` objects (mike's real shape) or bare
 * version strings. Entries that fail to parse sort last, preserving their
 * original relative order (stable sort). Never mutates the input.
 *
 * @param {Array<{version: string} | string> | null | undefined} versions
 * @returns {Array<{version: string} | string>}
 */
export function sortVersions(versions) {
  if (!Array.isArray(versions)) return [];
  const versionOf = (entry) => (typeof entry === 'string' ? entry : entry?.version);
  const decorated = versions.map((entry, index) => ({
    entry,
    index,
    parsed: parseVersion(versionOf(entry)),
  }));
  decorated.sort((a, b) => {
    if (a.parsed && b.parsed) return compareParsed(a.parsed, b.parsed);
    if (a.parsed) return -1; // parsed entries outrank unparseable ones
    if (b.parsed) return 1;
    return a.index - b.index; // both unparseable: preserve original order
  });
  return decorated.map((d) => d.entry);
}
