# Examples

Collection of runnable, self‑contained scripts illustrating common workflows.

## Available Scripts

| Script                        | Focus                                                                              | Run                                           |
| ----------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------- |
| `scalar_basic.py`             | Scalar add + anti-patterns + rollback demo                                         | `python examples/scalar_basic.py`             |
| `vector_basic.py`             | Base vector: stage component scalars first, then vector & implicit magnitude       | `python examples/vector_basic.py`             |
| `derived_scalar_operator.py`  | Operator-derived scalar: time derivative requires base scalar                      | `python examples/derived_scalar_operator.py`  |
| `derived_scalar_reduction.py` | Reduction-derived scalar: time average requires base scalar, enforced naming       | `python examples/derived_scalar_reduction.py` |
| `derived_vector_gradient.py`  | Operator-derived vector: gradient requires base scalar + component derived scalars | `python examples/derived_vector_gradient.py`  |
| `add_scalar.ipynb`            | Notebook version with incremental narrative & tests                                | Open in VS Code / Jupyter                     |

## Guidelines

- Examples live outside the package namespace to avoid adding non-library code to the installed wheel.
- Keep dependencies limited to the main package and standard library.
- Mirror any significant example in the documentation (e.g. Quick Start appendix).

Kind Particularities:

- scalar: minimal; ensure canonical unit format and description (see rollback pattern in `scalar_basic.py`).
- vector: all component scalars must be present (staged before vector insert); component names `<axis>_component_of_<vector>`.
- derived*scalar: provenance with `mode: operator` or `reduction`; name pattern enforced (e.g. `time_derivative_of*<base>`).
- derived_vector: same naming/provenance rules plus component derived scalars existing ahead of vector insert.

Contributions: add a short docstring explaining steps, prefer explicit prints over implicit state. Provide rollback examples where mutation safety is relevant.
