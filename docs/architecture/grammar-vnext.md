# Canonical Grammar

> **Status**: Current specification.
> **Scope**: Defines strict validation, the recursive intermediate
> representation (IR), canonical rendering, and operator-expression parsing.

## Public parsing contract

The package-level grammar surface is:

```python
from imas_standard_names import StandardNameIR, compose, parse

result = parse("square_of_inverse_of_pressure", strict=True)
assert isinstance(result.ir, StandardNameIR)
assert [operator.op for operator in result.ir.operators] == ["square", "inverse"]
assert compose(result.ir) == "square_of_inverse_of_pressure"
```

`parse(name, strict=True)` is the authoritative validity oracle. It validates
closed vocabulary, segment semantics, recursive operator semantics, precedence,
and canonical spelling over the lossless IR.

The default `parse(name)` mode is diagnostic. It returns the same IR shape and
diagnostics but deliberately omits some strict semantic gates.
`validate_round_trip(name)` is also diagnostic: it asks only whether
`compose(parse(name).ir) == name`.

`parse_standard_name(name)` is a strict-validating projection into the flat
`StandardName` facade. A valid expression can exceed that facade, particularly
when one binary operator contains another. Projection failure does not overturn
the strict parser's validity result.

## Closed vocabulary and canonical output

Every grammatical segment is registry-backed. The parser may diagnose an
advisory alias, but strict validation accepts only the unique canonical
spelling. `compose(ir)` emits that spelling and raises instead of inventing a
fallback.

The registry is authoritative for operator kind, rendering template, precedence,
separator, index parameters, argument kinds, and semantic flags. Operator tokens
are bare: the template supplies `_of_` or the binary connector.

## Recursive IR

```text
StandardNameIR := {
    operators:  [OperatorApplication],       # outermost first
    projection: AxisProjection | None,
    qualifiers: [Qualifier],
    base:       QuantityOrCarrier,
    locus:      LocusRef | None,
    mechanism:  Process | None,
}

OperatorApplication := {
    kind: "unary_prefix" | "unary_postfix" | "binary",
    op:   Token,
    args: [StandardNameIR],
    separator: "and" | "to" | None,
}
```

The IR is recursive:

- A unary chain is ordered outermost first. A unary application can carry one
  explicit `StandardNameIR` operand; the compact form uses the remaining
  operator stack and enclosing core as that operand.
- A binary application always carries two ordered `StandardNameIR` operands.
  The left and right branches retain their own operator trees.
- `compose()` preserves authored operator order. It does not commute,
  reassociate, or simplify expressions.

For `square_of_inverse_of_pressure`, the operator list is `square`, then
`inverse`. For
`ratio_of_ratio_of_electron_density_to_ion_density_to_square_of_magnetic_field_magnitude`,
the outer ratio's left operand is itself a ratio tree. The flat facade cannot
represent that second form, but the recursive IR can.

## Operator templates

| Kind | Canonical template | Arity |
|------|--------------------|-------|
| Unary prefix | `<op>_of_<inner>` | one |
| Bare unary prefix | `<op>_<inner>` | one, only for registry-declared bare spellings |
| Unary postfix | `<inner>_<op>` | one |
| Binary | `<op>_of_<A>_<separator>_<B>` | two |

Binary `product` and `difference` use `_and_`; `ratio` uses `_to_`.
Indexed operators bind their registered indices without changing the recursive
shape. For example, `derivative_with_respect_to` accepts a coordinate index,
while indexed postfix operators use their own registered parameters.

The operator registry contains unary prefix, unary postfix, and binary entries.
Its precedence values currently range from root decorators through
decompositions and algebraic transforms to reductions and modal or indexed
forms. Higher precedence wraps farther out. Equal-precedence operators retain
their authored order:

```text
square_of_inverse_of_pressure
inverse_of_square_of_pressure
```

These are distinct valid trees. In contrast, a lower-precedence operator cannot
wrap a higher-precedence operator in the wrong order.

The full current token inventory and metadata are generated from the operator
registry in the [grammar reference](../grammar-reference.md#operators).

## Binary splitting and associativity

A binary surface form has no parentheses, so the explicit nested operator
prefixes carry the tree structure. The parser:

1. identifies the outer registered binary operator and its declared connector;
2. tries connector positions from right to left;
3. recursively parses both candidate operands;
4. accepts the first split for which both branches resolve;
5. retains that ordered tree exactly.

This rule prevents `_to_` or `_and_` inside a registered operand from forcing a
bad split. It also defines surface associativity without algebraic
reinterpretation: nested binary operators must be spelled explicitly, and
rendering reproduces the chosen tree.

Recursive exploration memoizes both successful parses and failures by substring
and validation mode. Ambiguous or adversarial connector chains therefore do not
re-parse the same candidate operands repeatedly.

## Strict semantic validation

After structural parsing, strict mode recursively checks:

- operator registration, kind, separator, indexed form, and precedence;
- closed vocabulary for every binary operand;
- operator argument-kind and expression-kind constraints;
- flat segment compatibility within every wrapped core;
- generic-base qualification;
- state-to-species compatibility;
- flux-surface reduction semantics through nested unary and binary branches;
- byte-identical canonical rendering.

Wrapping an invalid flat core in operators cannot make it valid. Likewise, an
unknown locus or mechanism on a recursive binary tree remains invalid.

## Projection, qualifiers, loci, and mechanisms

Projection is typed by the base:

- an axis over a quantity is a component, such as `radial_magnetic_field`;
- an axis over a geometry carrier is a coordinate, such as
  `radial_position_of_flux_loop`.

Qualifiers use registry-defined canonical order. Scoping qualifiers follow the
ordered category registry, and tokens within one category retain authored
order. The grammar never alphabetizes the complete qualifier list.

Relations keep their meaning:

| Relation | Role |
|----------|------|
| `_of_` | unary or binary operator application, or an entity/geometry locus |
| `_at_` | point-like locus |
| `_over_` | region locus |
| `_along_` | path locus |
| `_due_to_` | mechanism |

The parser peels a trailing postfix operator, mechanism, and locus before
resolving the outer prefix or binary expression and then the core. Registered
multi-word tokens remain atomic throughout this process.

## Cross-project contract

`get_grammar_context()["grammar"]` exposes:

- registry-derived vocabularies and canonical templates;
- the locus relation matrix and binary separators;
- segment-scoped advisory aliases;
- the package-level parse, compose, and IR entry points;
- the strict validity mode, diagnostic default, round-trip diagnostic mode,
  flat-projection boundary, and outermost-first operator order.

See [Project Boundary](boundary.md) for the stability commitment and
[Data Flow](data-flow.md) for how strict validation enters the publication
pipeline.
