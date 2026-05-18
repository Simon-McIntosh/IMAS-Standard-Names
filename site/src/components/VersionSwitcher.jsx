// Mike-style version selector. Renders nothing if `versions.json` was
// absent (404). The selector navigates by replacing the current segment
// of the location pathname with the chosen version (mike puts each
// version under its own subdirectory).
export function VersionSwitcher({ versions, current }) {
  if (!versions || versions.length === 0) return null;
  const onChange = (e) => {
    const v = e.target.value;
    // Replace the last path segment (which should be the current version
    // under mike) with the chosen one. Fall back to a same-origin
    // anchor-style navigation if the path doesn't look versioned.
    const url = new URL(window.location.href);
    const segs = url.pathname.split('/').filter(Boolean);
    if (segs.length > 0) {
      segs[segs.length - 1] = v;
      url.pathname = '/' + segs.join('/') + '/';
    } else {
      url.pathname = `/${v}/`;
    }
    window.location.href = url.toString();
  };
  return (
    <select
      className="version-switcher"
      value={current ?? ''}
      onChange={onChange}
      title="Switch catalog version"
    >
      {versions.map((v) => (
        <option key={v.version} value={v.version}>
          {v.title || v.version}
          {v.aliases?.length ? ` (${v.aliases.join(', ')})` : ''}
        </option>
      ))}
    </select>
  );
}
