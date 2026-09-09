# Path qualification field selection

## Measured cause

`PATH_BASES` contains `trajectory`, `outline`, and `contour`. The semantic rule
read only `parsed.object`, but the parser stores the entity from qualified
outline names in `parsed.geometry`; `parsed.object` is `None`. The downstream
investigation found nine live rows containing the resulting issue phrase.

## Observed issue lists

| Name | Issue list before field selection | Issue list after field selection |
| --- | --- | --- |
| `radial_outline_of_plasma_boundary` | `ERROR - 'outline' must specify what entity's path/boundary is described` | `[]` |
| `radial_outline_of_wall` | `ERROR - 'outline' must specify what entity's path/boundary is described` | `[]` |
| `vertical_outline_of_plasma_boundary` | `ERROR - 'outline' must specify what entity's path/boundary is described` | `[]` |
| `outline` | `ERROR - 'outline' must specify what entity's path/boundary is described` | unchanged: same error |
| `trajectory` | `ERROR - 'trajectory' must specify what entity's path/boundary is described` | unchanged: same error |

The path check now accepts either `parsed.object` or `parsed.geometry`. It does
not change the path-base set or suppress the error for an unqualified name.

## Verification

Focused verification: `tests/test_semantic_path_qualification.py` — 5 passed
in 0.36s.

Full-suite verification: `pytest -p no:cacheprovider` completed with 2134
passed, 34 skipped, 82 xfailed, and zero failures at base revision
`2a4584d82537f3339e9c87294048ca4feb658495`; after the field selection it
completed with 2139 passed, 34 skipped, 82 xfailed, and zero failures. The
five additional passing tests are the focused path-qualification cases.
