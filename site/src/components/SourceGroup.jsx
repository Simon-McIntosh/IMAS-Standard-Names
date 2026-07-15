import { useState } from 'react';
import { ddDocumentationUrl } from '../lib/dd-links.js';

function SourcePreview({ source }) {
  const meaningfulParent = source.parent_definition && source.parent_path;
  const primary = meaningfulParent ? source.parent_definition : source.leaf_definition;
  return (
    <div className="source-preview" role="tooltip">
      <div className="source-preview-path mono">{source.path}</div>
      {source.dd_version && <div className="source-preview-version">DD {source.dd_version}</div>}
      {primary && <p>{primary}</p>}
      {meaningfulParent && (
        <div className="source-preview-parent">
          From parent <span className="mono">{source.parent_path}</span>
        </div>
      )}
      {meaningfulParent && source.leaf_definition && source.leaf_definition !== primary && (
        <div className="source-preview-leaf">Leaf: {source.leaf_definition}</div>
      )}
      {source.enhanced_context && (
        <div className="source-preview-enhanced">
          <strong>Derived context</strong>{source.enhancement_kind ? ` · ${source.enhancement_kind}` : ''}
          <p>{source.enhanced_context}</p>
        </div>
      )}
      <dl>
        {source.data_type && <><dt>Type</dt><dd>{source.data_type}</dd></>}
        {source.unit && <><dt>Unit</dt><dd>{source.unit}</dd></>}
        {source.coordinates && <><dt>Coordinates</dt><dd>{Array.isArray(source.coordinates) ? source.coordinates.join(', ') : source.coordinates}</dd></>}
        {source.lifecycle && <><dt>Lifecycle</dt><dd>{source.lifecycle}</dd></>}
        {source.semantic_facet && <><dt>Facet</dt><dd>{source.semantic_facet}</dd></>}
      </dl>
    </div>
  );
}

// Collapsible card grouping sources by IDS root. The path shown per row
// has the IDS prefix stripped because it's already in the group heading.
export function SourceGroup({ ids, items }) {
  const [open, setOpen] = useState(true);
  const [preview, setPreview] = useState(null);
  const groupVersion = items.find((item) => item.dd_version)?.dd_version;
  const idsUrl = ddDocumentationUrl(ids, groupVersion, { idsOnly: true });
  return (
    <div className="source-group">
      <div className="source-group-head">
        <button className="source-group-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="caret">{open ? '▾' : '▸'}</span>
        <span className="source-type">DD</span>
        </button>
        {idsUrl ? (
          <a className="mono source-ids-link" href={idsUrl} target="_blank" rel="noreferrer">{ids} ↗</a>
        ) : <span className="mono source-ids-link is-unlinked" title="Pinned DD version unavailable">{ids}</span>}
        <span className="source-group-count">{items.length}</span>
      </div>
      {open && (
        <div className="source-group-body">
          {items.map((s, i) => {
            const url = ddDocumentationUrl(s.path, s.dd_version);
            const shownPath = s.path.slice(ids.length + 1);
            return (
            <div className="source-item" key={`${s.path}-${i}`} onMouseLeave={() => setPreview(null)}>
              {url ? (
                <a className="source-path mono" href={url} target="_blank" rel="noreferrer"
                  onFocus={() => setPreview(i)} onMouseEnter={() => setPreview(i)}>
                  {shownPath} ↗
                </a>
              ) : (
                <span className="source-path mono" title="Pinned DD version unavailable; link disabled">{shownPath}</span>
              )}
              <button className="source-info" aria-label={`Show source information for ${s.path}`}
                aria-expanded={preview === i} onClick={() => setPreview(preview === i ? null : i)}
                onFocus={() => setPreview(i)}>i</button>
              {preview === i && <SourcePreview source={s} />}
            </div>
          )})}
        </div>
      )}
    </div>
  );
}
