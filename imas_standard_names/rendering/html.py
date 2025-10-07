"""HTML rendering for Standard Name entries.

Lightweight, dependency-optional: if `markdown` is unavailable, fall back to plain text.
"""

from __future__ import annotations

try:  # optional dependency
    import markdown  # type: ignore
except Exception:  # pragma: no cover
    markdown = None  # type: ignore

from ..models import StandardNameEntryBase

__all__ = ["render_html"]


def _md(text: str) -> str:
    if not text:
        return ""
    if markdown is None:
        return f"<p>{text}</p>"
    return markdown.markdown(text)


def render_html(
    entry: StandardNameEntryBase, extended_doc: str = "", include_empty: bool = False
) -> str:
    """Return an HTML fragment representing a standard name.

    Parameters
    ----------
    entry : StandardNameEntryBase
        The validated schema model instance.
    extended_doc : str
        Optional richer documentation (sidecar markdown, etc.).
    include_empty : bool
        If True, include rows for empty governance fields (default False).
    """
    rows = []

    def add_row(label: str, value):
        if value in (None, "", [], {}) and not include_empty:
            return
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            value = ", ".join(f"{k}:{v}" for k, v in value.items())
        rows.append(f"<tr><th>{label}</th><td>{value}</td></tr>")

    # Core block
    html = [f"<div class='standard-name' id='{entry.name}'>", f"<h2>{entry.name}</h2>"]
    if entry.description:
        html.append(f"<div class='description'>{_md(entry.description)}</div>")
    if extended_doc:
        html.append(f"<div class='documentation'>{_md(extended_doc)}</div>")

    # Table of attributes
    add_row("Kind", getattr(entry, "kind", None))
    add_row("Status", getattr(entry, "status", None))
    unit_display = (
        entry.formatted_unit()
        if hasattr(entry, "formatted_unit")
        else getattr(entry, "unit", "")
    )
    if unit_display and unit_display != "1":
        add_row("Unit", unit_display)
    prov = getattr(entry, "provenance", None)
    if prov is not None:
        try:
            add_row(
                "Provenance",
                {k: v for k, v in prov.model_dump().items() if v not in (None, [], "")},
            )  # type: ignore[attr-defined]
        except Exception:
            add_row("Provenance", str(prov))
    add_row("Tags", getattr(entry, "tags", None))
    add_row("Constraints", getattr(entry, "constraints", None))
    add_row("Validity Domain", getattr(entry, "validity_domain", None))
    add_row("Deprecates", getattr(entry, "deprecates", None))
    add_row("Superseded By", getattr(entry, "superseded_by", None))

    if rows:
        html.append("<table class='details'>")
        html.extend(rows)
        html.append("</table>")
    html.append("</div>")
    return "\n".join(html)
