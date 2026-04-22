# Grammar vNext — Canonical-form Philosophy (rc21)

> **Status**: Specification (W1a, plan 38).
> **Scope**: Defines the canonical-form philosophy, the 5-group intermediate
> representation (IR), canonical rendering templates, and the `_of_`
> disambiguation rules that govern ISN grammar from rc21 onward.
> **Companion code**: `imas_standard_names/grammar/ir.py` (IR model),
> `imas_standard_names/grammar/render.py` (strict generator).
> **Non-goal**: This document does not specify the parser — see W2b.

## 1. Design philosophy

Grammar vNext is built on five design commitments. Every subsequent rule
flows from them.

### 1.1 Liberal parser, strict generator

- The **parser** (future `grammar/parser.py`, W2b) accepts known legacy and
  colloquial variants. It emits `Diagnostic(category="non_canonical", …)`
  annotations but always returns a valid IR when the residue resolves.
- The **generator** (`grammar/render.py::compose`) emits **exactly one**
  canonical string per IR. It has no fallbacks: malformed IR raises
  `RenderError` rather than producing a best-effort string.
- Round-trip safety is defined against the IR:
  `compose(parse(name).ir) == canonical_form(name)` for every valid name.

### 1.2 Relations keep their prepositions

The four relational prepositions are **preserved**:

| Preposition | Role | Example |
|---|---|---|
| `_of_` | locus / unary-operator application | `elongation_of_plasma_boundary` |
| `_at_` | evaluation at a point-like locus | `power_flux_density_at_inner_divertor_target` |
| `_over_` | evaluation over a region | `integral_over_plasma_volume` |
| `_due_to_` | mechanism / causal agent | `ion_momentum_flux_due_to_diamagnetic_drift` |

Plan 37's preposition-stripping proposal is rejected: prepositions carry
boundary and semantic information that is expensive to recover from a flat
token stream.

### 1.3 Prepositions are scarce, single-role resources

Each preposition marks **exactly one** semantic role. In particular:

- `_at_` — position-typed locus only
- `_over_` — region-typed locus only
- `_due_to_` — mechanism only
- `_of_` — operator application **or** entity-/position-typed locus (see §4)

This scarcity is what makes the grammar parseable without global backtracking.

### 1.4 Operators carry explicit scope markers

All operator templates render their scope marker inside the template engine,
not inside the operator token:

- Unary prefix operators render as `<op>_of_<inner>` — the `_of_` is emitted
  by `render.py`, not baked into the token string. The operator registry
  stores `magnitude`, not `magnitude_of`.
- Unary postfix operators render as `<inner>_<op>` — no preposition needed.
- Binary operators render as `<op>_of_<A>_<sep>_<B>` with the separator
  (`_and_`, `_to_`) disambiguating which branch is which.

This matters because it keeps one canonical place (the operator registry)
where operator semantics live, and it lets the parser peel operators via
longest-match against a clean bare-token vocabulary.

### 1.5 Closed vocabularies everywhere (no fallback)

Every segment of the IR — operators, qualifiers, base, axis, locus tokens,
processes — is backed by a **closed** YAML vocabulary. Permissive fallbacks
(rc20's open `physical_base` behaviour) are a latent bug: they let names
drift outside the reviewed vocabulary and defeat the round-trip guarantee.

## 2. Zero legacy acceptance

> **User decision 2026-04-22**: the codex `StandardName` corpus will be
> cleared and regenerated against rc21. **Do not accept rc20 non-canonical
> forms as valid output.**

Consequences for the grammar:

- The generator emits only the **vNext canonical form** for an IR. There is
  no "emit rc20-compatible variant" mode.
- The parser may still accept rc20 surface strings during the transition
  window — that is useful for corpus mining (§A9) — but every non-canonical
  input yields a `Diagnostic(category="non_canonical")`, and the IR is
  always re-rendered into the vNext canonical form before publication.
- There is no back-compatibility shim that preserves rc20 canonical output.
  Names that render differently under vNext will render differently. The
  ISNC corpus regeneration absorbs the change.

## 3. 5-group intermediate representation (IR)

The IR replaces rc20's 12 flat segments with five groups, one of which
(operators) is recursive.

```text
StandardNameIR := {
    operators:  [OperatorApplication],       # outer-to-inner stack
    projection: AxisProjection | None,       # <axis>_component / _coordinate
    qualifiers: [Qualifier],                 # species / source entity
    base:       QuantityBase | GeometryCarrier,
    locus:      LocusRef | None,             # _of_E / _at_L / _over_R
    mechanism:  Process | None,              # _due_to_P
}

OperatorApplication := {
    kind: "unary_prefix" | "unary_postfix" | "binary",
    op:   Token,                             # bare; registry-resolved
    args: [StandardNameIR],                  # unary: 1 arg; binary: 2 args
}

AxisProjection := {
    axis:  CoordinateAxis,                   # closed vocab
    shape: "component" | "coordinate",
}

LocusRef := {
    relation: "of" | "at" | "over",
    token:    LocusToken,                    # closed registry
    type:     "entity" | "position" | "region" | "geometry",
}
```

Rules:

- **Operators are a tree, not a flat list.** `maximum_of_derivative_of_X_with_respect_to_Y`
  has two nested operators; each `args[i]` is itself a `StandardNameIR`.
- **Projection is typed by base.** `shape=component` requires `base` to be a
  `QuantityBase`; `shape=coordinate` requires `base` to be a
  `GeometryCarrier`. This encodes the distinction that `radial_component_of_magnetic_field`
  is a quantity projection while `radial_coordinate_of_magnetic_axis` is a
  geometric coordinate lookup.
- **Qualifiers are plain prefix tokens** drawn from closed vocabularies
  (species, source entity). They are unordered conceptually, but render in
  a canonical order (see §4.3).
- **`base` is exactly one token** from either `physical_bases.yml` or
  `geometry_carriers.yml`. There is no "base stack" and no open fallback.
- **Locus is optional and typed.** The relation is chosen from the locus
  type via a compatibility matrix (§5); it is never a free choice.
- **Mechanism is optional** and drawn from the closed `processes.yml`.

## 4. Canonical rendering templates

The generator is a pure function `compose(ir) -> str`. Its structure is:

```text
compose(ir) :=
    render_operators(ir.operators, inner_fn)
        where inner_fn() :=
            [render_projection(ir.projection) + "_of_"]?
            [render_qualifiers(ir.qualifiers) + "_"]?
            base_token
            [render_locus(ir.locus)]?
            [render_mechanism(ir.mechanism)]?
```

### 4.1 `render_operators(ops, inner_fn)`

Apply operators outer-to-inner. Outer = first element of the list.

- `unary_prefix`: `"<op>_of_<rest>"` where `<rest>` is the recursive rendering
  of the remaining operator list applied to `inner_fn()`.
- `unary_postfix`: `"<rest>_<op>"` (no preposition).
- `binary`: `"<op>_of_<A>_<sep>_<B>"` where `A` and `B` are `compose(args[0])`
  and `compose(args[1])` respectively; `<sep>` ∈ {`and`, `to`} determined by
  the operator's registered separator.

### 4.2 `render_projection(projection)`

- `shape=component` → `"<axis>_component"`
- `shape=coordinate` → `"<axis>_coordinate"` (only valid when base is a
  `GeometryCarrier`)

The trailing `_of_` is emitted by the surrounding template, not by
`render_projection`.

### 4.3 `render_qualifiers(qualifiers)`

Qualifiers render in **stable canonical order**: lexicographic by token
string. Multi-qualifier names are rare in practice, but when they occur the
ordering must be deterministic so that distinct permutations do not render
to distinct strings.

### 4.4 `render_locus(locus)`

- `locus` is rendered as `"_<relation>_<token>"`.
- `relation` is validated against `locus.type` via the compatibility matrix
  (§5). A mismatch raises `RenderError`.
- The locus suffix is always the **last `_of_`** in a name (trailing-position
  rule), which is what lets the parser identify it in §A8.

### 4.5 `render_mechanism(mechanism)`

- Renders as `"_due_to_<process>"`.
- Always trailing — after the locus, if both are present.

## 5. Locus relation compatibility matrix

```text
type       | of  | at  | over
-----------+-----+-----+------
entity     |  ✓  |  ·  |  ·
position   |  ✓  |  ✓  |  ·
region     |  ·  |  ·  |  ✓
geometry   |  ✓  |  ·  |  ·
```

- `entity` and `geometry` accept only `_of_` (they answer "of what").
- `position` accepts `_of_` and `_at_` (both "where" relations; parser
  chooses by context, generator renders whatever the IR specifies).
- `region` accepts only `_over_` (regions are extended, not point-like).

Applying the wrong relation to a typed locus is a **hard error** in the
generator and a **diagnostic** in the parser.

## 6. `_of_` disambiguation — exactly three roles

After vNext, `_of_` appears only in the following structural positions.
The parser uses these rules to unambiguously classify every `_of_` it sees.

| Role | Template | Disambiguator |
|---|---|---|
| **Unary prefix operator** | `<op>_of_<inner>` | `<op>` matches the operator registry via **longest-match-first**; `<inner>` is a recursively parseable IR. |
| **Binary operator** | `<op>_of_<A>_<sep>_<B>` | Mandatory `_and_` or `_to_` separator in the tail. |
| **Locus relation** | `…_of_<LocusToken>` | Always **trailing position**. The final `_of_` in a name is always a locus relation, provided the trailing token is in `locus_registry.yml` with `of ∈ allowed_relations`. |

### 6.1 Assertion helpers (encoded in code)

The IR model and `render.py` encode three assertion helpers that pin these
rules at runtime:

- `assert_operator_of_form(op, registry)` — an `OperatorApplication` with
  `kind=unary_prefix` must resolve `op` to a registered prefix operator.
- `assert_binary_has_separator(op, registry)` — an `OperatorApplication`
  with `kind=binary` must resolve to an operator whose registry entry
  declares a separator (`and` or `to`).
- `assert_locus_is_trailing(ir)` — at render time, the locus suffix is the
  final `_<relation>_<token>` segment in the rendered string, followed only
  by an optional `_due_to_<process>` mechanism tail.

These helpers are invoked from the IR's Pydantic validators and from
`compose()` as safety nets. They are **not** registry lookups themselves —
the registries are wired in later waves (W1c/W2a for vocabularies, W2b for
parser integration). Until then, the helpers accept a registry argument
(which may be a `dict`, a `Mapping`, or `None` for pure-shape checks).

### 6.2 Forms explicitly rejected by vNext

All rc20 usages of `_of_` that do not fit one of the three roles above are
rejected by the parser in W2b. This spec documents them so that the
classification in A9 can treat them as rewrite targets rather than valid
inputs:

- **Free-form "property of object" where the trailing token is not a
  registered locus.** Must be either added to `locus_registry.yml` or
  rewritten.
- **Component-prefix `_of_`** (rc20 `radial_component_of_magnetic_field`).
  vNext canonical is the same string (`radial_component_of_…`), but in
  vNext that `_of_` is the **operator-application `_of_`** rendered by the
  projection template, not a locus relation. The parser distinguishes it
  because it is immediately preceded by a closed `CoordinateAxis` token
  followed by `_component` or `_coordinate`.
- **Baked-in operator tokens** (rc20 `magnitude_of`, `time_derivative_of`).
  The operator registry stores bare `magnitude`, `time_derivative`; the
  `_of_` is emitted by `render_operators`.
- **Double-`_of_` locus ambiguity** (rc20
  `toroidal_component_of_magnetic_moment_of_ferritic_element_centroid`).
  vNext requires the component to render as postfix when the name already
  carries a locus suffix, so the final `_of_` is unambiguously the locus.

## 7. Relationship to existing rc20 modules

For the duration of W1a the vNext modules (`ir.py`, `render.py`) live
alongside the rc20 surface (`grammar/model.py`, `grammar/support.py`). No
existing module is modified or removed. W2b owns the parser cutover and the
eventual deletion of `support.py::parse_standard_name`.

## 8. References

- Plan 38 — `plans/features/standard-names/38-grammar-vnext.md` in imas-codex
  (sections A0–A3, A12).
- Grammar review — `files/grammar-review-copilot.md` in imas-codex.
- Boundary contract — `docs/architecture/boundary.md` in this repo.
