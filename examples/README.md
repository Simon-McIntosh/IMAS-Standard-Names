# Examples

Collection of runnable, self‑contained scripts illustrating common workflows.

## Documentation Examples

For worked examples showing how to map IMAS Data Dictionary paths to standard names:

- [IMAS Magnetics Diagnostic Example](../docs/magnetics-example.md) - Complete analysis of magnetics IDS paths including magnetic field components, time derivatives, and flux measurements

## Available Scripts

| Script                        | Focus                                                                              | Run                                           |
| ----------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------- |
| `scalar_basic.py`             | Scalar add + anti-patterns + rollback demo                                         | `python examples/scalar_basic.py`             |
| `vector_basic.py`             | Base vector: stage component scalars first, then vector & implicit magnitude       | `python examples/vector_basic.py`             |
| `derived_scalar_operator.py`  | Scalar with operator provenance: time derivative requires base scalar              | `python examples/derived_scalar_operator.py`  |
| `derived_scalar_reduction.py` | Scalar with reduction provenance: time average requires base scalar                | `python examples/derived_scalar_reduction.py` |
| `derived_vector_gradient.py`  | Vector with operator provenance: gradient requires base scalar + component scalars | `python examples/derived_vector_gradient.py`  |
| `add_scalar.ipynb`            | Notebook version with incremental narrative & tests                                | Open in VS Code / Jupyter                     |

## Guidelines

- Examples live outside the package namespace to avoid adding non-library code to the installed wheel.
- Keep dependencies limited to the main package and standard library.
- Mirror any significant example in the documentation (e.g. Quick Start appendix).

Kind Particularities:

- scalar: minimal; ensure canonical unit format and description (see rollback pattern in `scalar_basic.py`).
- scalar with provenance: add provenance with `mode: operator` or `reduction`; name pattern enforced (e.g. `time_derivative_of_<base>`).
- vector: all component scalars must be present (staged before vector insert); component names `<axis>_component_of_<vector>`.
- vector with provenance: same as vector, plus provenance block; component scalars must exist before vector.

Contributions: add a short docstring explaining steps, prefer explicit prints over implicit state. Provide rollback examples where mutation safety is relevant.
