const DD_DOCS_ROOT = 'https://imas-data-dictionary.readthedocs.io/en';

export function ddIds(path) {
  return String(path || '').split('/')[0] || '';
}

export function ddDocumentationUrl(path, version, { idsOnly = false } = {}) {
  const cleanPath = String(path || '').replace(/^\/+|\/+$/g, '');
  const cleanVersion = String(version || '').trim();
  const ids = ddIds(cleanPath);
  if (!cleanPath || !cleanVersion || !ids) return null;
  const page = `${DD_DOCS_ROOT}/${encodeURIComponent(cleanVersion)}/generated/ids/${encodeURIComponent(ids)}.html`;
  if (idsOnly) return page;
  const anchor = cleanPath.replace(/\//g, '-');
  return `${page}#${anchor}`;
}
