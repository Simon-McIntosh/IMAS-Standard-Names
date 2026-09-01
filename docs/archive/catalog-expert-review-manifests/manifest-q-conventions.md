# Manifest — f-q-conventions (rows 15 & 16)

Read-only investigation. No graph mutation, no commit, no plan edit performed.
Live graph link proven via `imas-codex sn status` (3876 StandardNames).

## Authoritative DD + COCOS evidence

DD served by imas-dd MCP — **current version 4.1.0** (range 3.22.0 → 4.1.1; 35 versions).

Path `equilibrium/time_slice/profiles_1d/q` (IDS equilibrium, FLT_1D, physics domain equilibrium):

- **COCOS transform class = `q_like`** (added at DD **v3.28.1** via `cocos_label_transformation`).
  q_like is the 30-field family (`.../profiles_1d/q`, `q_axis`, `q_95`, `q_min/value`, …).
  Under a COCOS sign reversal a q_like field **reverses its stored value**; the geometric
  locus it labels is unaffected. This is exactly the invariant the locked row-16 decision preserves.
- **Authoritative sign wording** (DD documentation field, tracked across versions):
  - v3.30.0: `Safety factor` → `Safety factor (IMAS uses COCOS=11: only positive when toroidal current and magnetic field are in same direction)`
  - v4.0.0: `… (IMAS uses COCOS=11: only positive when toroidal current and magnetic field are in same direction)` → **`Safety factor (only positive when toroidal current and magnetic field are in same direction)`**
    (the explicit "IMAS uses COCOS=11:" text was moved out of the prose into the q_like metadata; the physics statement is unchanged.)
  - Same edit applied to `q_95`.
- Bulk query `change_type_filter=sign_convention, ids_filter=equilibrium` → **0 changes**: the DD carries q's sign in the q_like COCOS metadata, not as a per-version "sign_convention" flag. No unresolved DD sign defect exists on this path.

**Authoritative sign relation that SHOULD appear (COCOS=11 / q_like):**
> q is positive **iff the toroidal magnetic field B_φ and the toroidal plasma current I_p are parallel (same direction)**, negative iff antiparallel. The sign depends only on the *relative* orientation of B_φ and I_p and is invariant under a relabelling of the toroidal-angle direction; reversing either B_φ or I_p alone flips the sign.

---

## ROW 15 — Safety-factor SIGN convention

### Verdict: **CATALOG WORDING DEFECT** (not a DD defect). Reword to match DD/COCOS=11.

The disputed catalog sentence on `safety_factor` reads:

> "Sign convention: Positive when the toroidal magnetic field $B_\phi$ and the plasma current $I_p$ are **both directed in the sense of increasing toroidal angle $\phi$**."

Why it is wrong (and the DD is right):

- COCOS=11 fixes q's sign by the **relative alignment** of B_φ and I_p (DD: "same direction"),
  which is invariant under an (arbitrary) choice of which way φ increases.
- "Both directed in **increasing** φ" is **not** invariant under that relabelling and captures
  only the (+φ, +φ) case. It **wrongly excludes the (−φ, −φ) case**, which is equally
  "same direction" and therefore equally q > 0. The catalog sentence is over-restrictive /
  gauge-dependent — a wording error, not a physics/DD error. The DD wording needs no upstream issue.

**Corrected sentence (drop-in replacement for the final "Sign convention:" line):**

> Sign convention (COCOS=11): $q$ is positive when the toroidal magnetic field $B_\phi$ and the toroidal plasma current $I_p$ are parallel (aligned in the same sense along $\phi$) and negative when they are antiparallel. The sign depends only on the relative orientation of $B_\phi$ and $I_p$ — it is unchanged if the direction of increasing toroidal angle $\phi$ is relabelled — and it reverses if either $B_\phi$ or $I_p$ alone is reversed.

### Every safety-factor-family standard name (queried `id CONTAINS 'safety_factor'`, 10 names)

All 10 are `name_stage=accepted`, `validation_status=valid`.

| # | Standard name | Current sign sentence | Affected by row 15? |
|---|---|---|---|
| 1 | `safety_factor` | "…both directed **in the sense of increasing** toroidal angle φ." | **YES — defect (exact disputed phrase)** |
| 2 | `safety_factor_at_pedestal_top` | "…both directed **toward increasing** toroidal angle φ in the right-handed cylindrical (R,φ,Z) frame…" | **YES — same defect (paraphrase)** |
| 3 | `safety_factor_at_magnetic_axis` | "Positive when magnetic field lines advance in the direction of increasing φ for an advance in positive poloidal angle θ…" (pitch dφ/dθ>0) | No — COCOS-consistent, gauge-invariant |
| 4 | `safety_factor_at_internal_transport_barrier` | "Positive when the field-line slope dφ/dθ is positive…" | No — COCOS-consistent |
| 5 | `safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95` | "Positive when signed toroidal flux increases with signed poloidal flux across neighbouring surfaces…" | No — COCOS-consistent |
| 6 | `minimum_safety_factor` | "Positive when the toroidal angle advance … is in the direction of increasing φ as θ increases…" (pitch) | No for row 15 (but rewritten under row 16) |
| 7 | `normalized_toroidal_flux_coordinate_at_minimum_safety_factor` | sign sentence is about the toroidal-flux coordinate, not q | No for row 15 (rewritten under row 16) |
| 8 | `poloidal_magnetic_flux_at_minimum_safety_factor` | sign sentence is about poloidal-flux orientation, not q | No for row 15 (rewritten under row 16) |
| 9 | `normalized_poloidal_flux_coordinate_at_minimum_safety_factor` | no "Sign convention" line (dimensionless locator) | No for row 15 (rewritten under row 16) |
| 10 | `safety_factor_at_plasma_boundary` | **`documentation` IS NULL** (accepted name with empty docs) | Flagged — see remaining decisions |

**Row-15 names to edit: exactly `safety_factor` and `safety_factor_at_pedestal_top`.** Names 3–5 already express the sign in a COCOS-consistent, gauge-invariant form and need no change. The pitch-based (dφ/dθ) statements are equivalent to the parallel-alignment rule and are correct.

---

## ROW 16 — minimum q → arg min |q| (locked decision)

Locked: **locus = arg min |q|**; **stored q_min value = signed q at that locus** (preserves the q_like transform).

Four names use plain `min q` / `arg min q` (signed) and must switch the *locus* selector to `arg min |q|`:

| Standard name | What it stores | Current selector | Corrected selector |
|---|---|---|---|
| `minimum_safety_factor` | the q_min **value** | `q_min = min q(ρ)` (min of signed q) | `q_min = q(ρ*)`, ρ* ∈ arg min\|q\| — **signed value at the min-\|q\| locus** |
| `poloidal_magnetic_flux_at_minimum_safety_factor` | ψ of the locus | `χ* ∈ arg min q(χ)` | `χ* ∈ arg min \|q(χ)\|` |
| `normalized_poloidal_flux_coordinate_at_minimum_safety_factor` | ψ_N of the locus | `arg min q(ψ_N)` | `arg min \|q(ψ_N)\|` |
| `normalized_toroidal_flux_coordinate_at_minimum_safety_factor` | ρ_tor,N of the locus | "globally minimizes q(ρ_tor,N)" | "globally minimizes \|q(ρ_tor,N)\|" |

For a single-signed (all-positive) q-profile — the ordinary tokamak case — arg min\|q\| = arg min q, so this is a
no-op there; the distinction only bites for sign-changing / reversed-field profiles, and it keeps the value signed.

### One-line reworded definition intent per name (full drop-in text in the "Executor" section)

- **`minimum_safety_factor`** — "…is the signed safety factor evaluated on the closed flux surface where the *magnitude* of the safety factor is smallest (the value of q at arg min |q|), not the algebraic minimum of signed q."
- **`poloidal_magnetic_flux_at_minimum_safety_factor`** — "…the poloidal flux on the surface that minimises |q|; χ* ∈ arg min_χ |q(χ)|."
- **`normalized_poloidal_flux_coordinate_at_minimum_safety_factor`** — "…ψ_N on the surface where |q| is globally smallest; ψ_{N,q_min} = arg min |q(ψ_N)|."
- **`normalized_toroidal_flux_coordinate_at_minimum_safety_factor`** — "…ρ_tor,N on the surface that globally minimises |q(ρ_tor,N)|."

---

## EXECUTOR COMMANDS

`sn edit` verified: `uv run imas-codex sn edit STANDARD_NAME (--hint|--rename|--docs) --reason ... [--dry-run] [--scope self]`.
`--docs` **replaces the whole documentation** and rides the review→score pipeline (successor lands accepted or reports below-threshold). `--reason` is mandatory. **Always `--dry-run` first.** All six edits are leaf/self scope (`--scope self`).

> NOTE ON QUOTING: the replacement docs contain `$…$`, `\`, `{`, `}`, backticks and newlines. Passing them via `--docs "…"` on the shell will mangle them. **Executor should pass each doc from a file** (e.g. `--docs "$(cat body.md)"` with the body written verbatim to a scratch file), or the pipeline will corrupt the LaTeX. The exact bodies are given below verbatim — write each to a file, then substitute.

### Row 15 — command shape

```bash
# 1. safety_factor  (--dry-run first, then drop --dry-run)
uv run imas-codex sn edit safety_factor --scope self --dry-run \
  --reason "COCOS=11/q_like (DD equilibrium/time_slice/profiles_1d/q, v4.0.0): q>0 iff B_phi and I_p are PARALLEL, not 'both in +phi'. Current sentence is gauge-dependent and wrongly excludes the (-phi,-phi) same-direction case." \
  --docs "$(cat /path/to/safety_factor.body)"

# 2. safety_factor_at_pedestal_top  (same defect, paraphrase)
uv run imas-codex sn edit safety_factor_at_pedestal_top --scope self --dry-run \
  --reason "Same COCOS=11/q_like sign fix as safety_factor: 'both directed toward increasing toroidal angle' is gauge-dependent; DD sign rule is relative alignment (B_phi parallel I_p)." \
  --docs "$(cat /path/to/safety_factor_at_pedestal_top.body)"
```

### Row 16 — command shape

```bash
uv run imas-codex sn edit minimum_safety_factor --scope self --dry-run \
  --reason "Locked decision: q_min locus = arg min |q| (absolute-q); stored value = signed q at that locus. Preserves DD q_like transform (sign reversal leaves locus fixed, flips value)." \
  --docs "$(cat /path/to/minimum_safety_factor.body)"

uv run imas-codex sn edit poloidal_magnetic_flux_at_minimum_safety_factor --scope self --dry-run \
  --reason "Locked decision: minimum-q locus = arg min |q|, not arg min signed q. Flux label reads the min-|q| surface." \
  --docs "$(cat /path/to/poloidal_magnetic_flux_at_minimum_safety_factor.body)"

uv run imas-codex sn edit normalized_poloidal_flux_coordinate_at_minimum_safety_factor --scope self --dry-run \
  --reason "Locked decision: locus = arg min |q| (absolute-q)." \
  --docs "$(cat /path/to/normalized_poloidal_flux_coordinate_at_minimum_safety_factor.body)"

uv run imas-codex sn edit normalized_toroidal_flux_coordinate_at_minimum_safety_factor --scope self --dry-run \
  --reason "Locked decision: locus = arg min |q| (absolute-q)." \
  --docs "$(cat /path/to/normalized_toroidal_flux_coordinate_at_minimum_safety_factor.body)"
```

---

## VERBATIM REPLACEMENT BODIES

Only the marked sentence/formula changed vs. the current graph text; everything else is preserved.

### safety_factor.body

The safety factor $q(\psi)$ measures the helical winding of magnetic field lines on a given flux surface: it equals the number of complete toroidal transits a field line completes for each poloidal circuit around the inner plasma region.

The formal definition relates $q$ to the ratio of magnetic flux increments:

$$
q = \frac{d\Phi_{\rm tor}}{d\Phi_{\rm pol} / (2\pi)}
$$

where $\Phi_{\rm tor}$ is the toroidal magnetic flux (Wb) enclosed within the flux surface and $\Phi_{\rm pol}$ is the poloidal magnetic flux (Wb) encircled by the flux-surface boundary. Surfaces where $q = m/n$ (integers $m$, $n$) are resonant with magnetohydrodynamic perturbations of poloidal mode number $m$ and toroidal mode number $n$, enabling tearing modes and neoclassical tearing modes; the $q = 1$ resonant surface underpins sawtooth instabilities, and the $q = 2$ surface is associated with the onset of neoclassical tearing modes in high-performance discharges.

In conventional H-mode operation, the [safety factor at the magnetic axis](name:safety_factor_at_magnetic_axis) is typically near 1, while the [safety factor at the 95% normalized poloidal flux surface](name:safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95) lies in the range 3–5. Reversed-shear configurations have an interior $q$ minimum, and elevated $q$ at the [pedestal](name:safety_factor_at_pedestal_top) constrains edge stability. The $q$ profile is inferred from equilibrium reconstruction augmented by internal measurements such as motional Stark effect polarimetry or Faraday rotation; it is also evaluated locally on individual flux surfaces in gyrokinetic turbulence simulations.

Sign convention (COCOS=11): $q$ is positive when the toroidal magnetic field $B_\phi$ and the toroidal plasma current $I_p$ are parallel (aligned in the same sense along $\phi$) and negative when they are antiparallel. The sign depends only on the relative orientation of $B_\phi$ and $I_p$ — it is unchanged if the direction of increasing toroidal angle $\phi$ is relabelled — and it reverses if either $B_\phi$ or $I_p$ alone is reversed.

### safety_factor_at_pedestal_top.body

The safety factor at the pedestal, often denoted $q_\mathrm{ped}$, is the value of the [safety factor](name:safety_factor) on the flux surface associated with the H-mode pedestal. It characterizes magnetic-field-line winding: the number of toroidal turns in the right-handed cylindrical $(R, \phi, Z)$ frame per poloidal turn around the inner plasma region on the steep-gradient edge transport-barrier flux surface.

The formal definition is inherited from the flux-increment definition of $q$ and evaluated at the pedestal flux surface:

$$
q_\mathrm{ped} = \left. \frac{d\Phi_{\rm tor}}{d\Phi_{\rm pol}/(2\pi)} \right|_{\rm pedestal}
$$

where $\Phi_{\rm tor}$ is the toroidal magnetic flux in Wb enclosed by the flux surface, $\Phi_{\rm pol}$ is the poloidal magnetic flux in Wb encircled by the flux-surface boundary, and the subscript denotes evaluation on the pedestal flux surface. Rational values $q_\mathrm{ped}=m/n$ align the pedestal with perturbations of poloidal mode number $m$ and toroidal mode number $n$, influencing edge magnetohydrodynamic stability and edge-localized-mode thresholds.

The pedestal flux surface is identified from the location of the strongest edge gradients in electron pressure, temperature, or density, with the pedestal top often near the normalized poloidal flux $\psi_N \approx 0.95$. The value is computed from magnetic equilibrium reconstruction constrained by magnetic measurements and, when available, internal current-profile constraints such as motional Stark effect polarimetry or Faraday rotation. Because the pedestal top is often close to $\psi_N=0.95$, $q_\mathrm{ped}$ is closely related to [safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95](name:safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95) but is tied to the measured pedestal location rather than to the fixed normalized poloidal flux value $\psi_N=0.95$.

In conventional H-mode tokamak plasmas, $q_\mathrm{ped}$ is commonly 3-6, with higher values in lower-current or deliberately high-$q$ operating points and lower values in high-current scenarios. It complements [safety_factor_at_internal_transport_barrier](name:safety_factor_at_internal_transport_barrier), [safety_factor_at_magnetic_axis](name:safety_factor_at_magnetic_axis), and [minimum_safety_factor](name:minimum_safety_factor) by locating the safety-factor function at the edge transport barrier.

Sign convention (COCOS=11): $q_\mathrm{ped}$ is positive when the toroidal magnetic field $B_\phi$ and the toroidal plasma current $I_p$ are parallel (aligned in the same sense along $\phi$) and negative when they are antiparallel. The sign depends only on the relative orientation of $B_\phi$ and $I_p$ — it is unchanged if the direction of increasing toroidal angle $\phi$ is relabelled — and it reverses if either $B_\phi$ or $I_p$ alone is reversed.

### minimum_safety_factor.body

Minimum safety factor is the signed safety factor evaluated on the closed magnetic flux surface where the magnitude of the safety factor is smallest — that is, the value of $q$ at the locus that minimizes $|q|$ over the nested closed flux surfaces. The safety factor on a surface is the field-line pitch, equal to the toroidal angle advance per poloidal circuit in flux coordinates $(\rho,\theta,\phi)$, with $\phi$ the toroidal angle of the right-handed cylindrical $(R,\phi,Z)$ frame where $R$ is major radius and $Z$ is vertical height. This quantity is the signed scalar value on that surface; the corresponding surface location is represented by [poloidal_magnetic_flux_at_minimum_safety_factor](name:poloidal_magnetic_flux_at_minimum_safety_factor).

The value is defined as the signed safety factor at the flux surface that minimizes its magnitude over the closed-surface domain:

$$
q_{\min} = q(\rho_\ast), \qquad \rho_\ast \in \operatorname*{arg\,min}_{0 \le \rho \le 1} |q(\rho)|
$$

where $\rho$ is a dimensionless monotonic flux-surface label normalized to 0 at the magnetic axis and 1 at the last closed flux surface, $q(\rho)$ is the signed safety factor (dimensionless), $\rho_\ast$ labels the surface of least $|q|$, and $q_{\min}=q(\rho_\ast)$ retains the sign of $q$ there. For the usual single-signed (everywhere-positive) $q$ profile this coincides with the ordinary minimum of $q$; the magnitude-based locus matters only for sign-changing profiles, and keeping the value signed is consistent with the Data Dictionary $q$-like COCOS transform (a reversal of the field-line helicity leaves the minimum-$|q|$ locus unchanged and flips the stored value). The result is independent of the particular monotonic label used, provided the same set of closed flux surfaces is covered.

In practice, $q_{\min}$ is obtained from an equilibrium reconstruction by computing $q$ on closed flux surfaces from the magnetic-field geometry and locating the surface of least magnitude, with interpolation between evaluated surfaces when needed. Magnetic measurements constrain the reconstruction, and kinetic or polarimetric constraints may improve the inferred current density and field-line pitch. The related point value [safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95](name:safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95) samples $q$ near the edge rather than taking a global minimum.

Typical tokamak values are about 0.7-2.5 for conventional or weakly reversed-shear plasmas. Values near 1 are important for internal-kink and sawtooth thresholds; crossing low-order rational values such as $3/2$ or $2$ can mark changes in resonant surfaces relevant to tearing and other MHD modes. Advanced or high-safety-factor scenarios may have $q_{\min}$ above 2.

Sign convention: Positive when the toroidal angle advance of a magnetic field line is in the direction of increasing $\phi$ as the poloidal angle $\theta$ increases in flux coordinates $(\rho,\theta,\phi)$.

### poloidal_magnetic_flux_at_minimum_safety_factor.body

Poloidal magnetic flux at minimum safety factor is the value of the poloidal magnetic flux on the closed flux surface where the magnitude of the safety factor reaches its minimum. It provides an absolute, dimensional flux label (in webers) for that surface, as opposed to the dimensionless normalized poloidal flux coordinate of the same surface.

The quantity is defined by selecting the flux surface that minimizes the magnitude of the safety factor and reading off its poloidal flux:

$$
\psi_{q_{\min}} = \psi(\chi_\ast), \qquad \chi_\ast \in \operatorname*{arg\,min}_{\chi \in \mathcal{D}} |q(\chi)|
$$

where $\psi$ is the poloidal magnetic flux in Wb, $q$ is the dimensionless signed safety factor, $\chi$ is any monotonic label ordering the nested closed flux surfaces of the domain $\mathcal{D}$, and $\chi_\ast$ labels a surface on which $|q|$ is least (so that the signed value there equals $q_\mathrm{min}$). The argmin form makes no assumption that the minimum is an interior extremum: it may occur at the magnetic axis, at an interior surface, or near the plasma boundary. The poloidal flux itself is the magnetic flux through a horizontal disk centered on the toroidal symmetry axis, $\psi(R,Z) = \int_0^R B_Z(R',Z)\,2\pi R'\,dR'$, and is defined only up to an arbitrary additive gage constant; only flux differences (for example relative to the magnetic axis or boundary) are physically meaningful.

In practice the quantity is obtained from an equilibrium reconstruction by evaluating $q$ over the nested closed flux surfaces, identifying the surface that attains the least $|q|$, and interpolating the corresponding $\psi$ value. The same surface can be expressed in dimensionless form by [normalized_poloidal_flux_coordinate_at_minimum_safety_factor](name:normalized_poloidal_flux_coordinate_at_minimum_safety_factor) via a normalization such as $\psi_N = (\psi - \psi_\mathrm{axis})/(\psi_\mathrm{boundary} - \psi_\mathrm{axis})$, where $\psi_\mathrm{axis}$ and $\psi_\mathrm{boundary}$ are the magnetic-axis and boundary fluxes; this removes the gage ambiguity inherent in the dimensional value.

Typical magnitudes scale with device size, plasma current, toroidal field, and the gage chosen for $\psi$, so absolute values are reported as flux differences from the magnetic axis. Monotonic-shear equilibria place the minimum at or near the magnetic axis, while reversed-shear configurations move it to mid-radius or farther out.

Sign convention: Positive when the poloidal magnetic flux through the enclosed horizontal disk centered on the toroidal symmetry axis is oriented along $+\hat{Z}$ in the right-handed cylindrical $(R, \phi, Z)$ frame, where $Z$ is vertical height.

### normalized_poloidal_flux_coordinate_at_minimum_safety_factor.body

Normalized poloidal flux coordinate at minimum safety factor is the value of the normalized poloidal flux coordinate $\psi_N$ on the flux surface where the magnitude of the [safety factor](name:safety_factor) $q$ is globally smallest inside the last-closed flux surface. It locates the minimum-$|q|$ surface relative to the magnetic axis and plasma boundary, independent of the dimensional scale of [poloidal magnetic flux](name:poloidal_magnetic_flux).

The quantity is defined by minimizing the magnitude of the safety factor as a function of normalized poloidal flux coordinate and applying the axis-to-boundary normalization of poloidal magnetic flux:

$$
\psi_{N,q_{\min}} = \operatorname*{arg\,min}_{0 \le \psi_N \le 1} |q(\psi_N)|, \qquad
\psi_N = \frac{\psi - \psi_\mathrm{axis}}{\psi_\mathrm{b} - \psi_\mathrm{axis}}
$$

where $\psi_{N,q_{\min}}$ is the coordinate of the minimum-$|q|$ surface, $q(\psi_N)$ is the signed safety factor on a closed flux surface, $\psi$ is the poloidal magnetic flux of that surface, $\psi_\mathrm{axis}$ is the value at the magnetic axis, and $\psi_\mathrm{b}$ is the value at the plasma boundary. The minimization is over closed flux surfaces in the confined plasma; if several surfaces share the same least magnitude, the arg-min is mathematically non-unique.

In practice this coordinate is computed from an equilibrium reconstruction by evaluating the safety-factor radial behavior on nested closed flux surfaces, identifying the surface of globally least $|q|$, and converting the corresponding surface to $\psi_N$. The corresponding dimensional flux on the same surface is [poloidal_magnetic_flux_at_minimum_safety_factor](name:poloidal_magnetic_flux_at_minimum_safety_factor); a toroidal-flux-radius analog is [normalized_toroidal_flux_coordinate_at_minimum_safety_factor](name:normalized_toroidal_flux_coordinate_at_minimum_safety_factor).

Typical values lie in the interval 0-1. Values near 0 indicate that the minimum safety factor is on or very close to the magnetic axis, while values around 0.2-0.6 are common for reversed-shear or otherwise non-monotonic equilibria with an off-axis minimum; values approaching 1 indicate a minimum near the plasma boundary.

### normalized_toroidal_flux_coordinate_at_minimum_safety_factor.body

The normalized toroidal flux coordinate $\rho_{\mathrm{tor,N}}$ evaluated at the minimum safety factor surface identifies the dimensionless radial location of the $q_{\min}$ surface within the plasma. This coordinate ranges from 0 at the magnetic axis to 1 at the plasma boundary, so its value distinguishes centrally located $q_{\min}$ surfaces (near-axis, values close to 0) from off-axis surfaces characteristic of reversed-shear plasmas (values in the range 0.3–0.7).

The [normalized toroidal flux coordinate](name:normalized_toroidal_flux_coordinate) is defined as:

$$
\rho_{\mathrm{tor,N}} = \sqrt{\frac{\Phi_{\mathrm{tor}}}{\Phi_{\mathrm{tor,b}}}}
$$

where $\Phi_{\mathrm{tor}}$ is the toroidal magnetic flux enclosed by a given flux surface and $\Phi_{\mathrm{tor,b}}$ is the total toroidal magnetic flux within the plasma boundary. This quantity is the value of $\rho_{\mathrm{tor,N}}$ at the flux surface that globally minimizes $|q(\rho_{\mathrm{tor,N}})|$, i.e. the surface of least safety-factor magnitude.

The location of $q_{\min}$ is extracted from equilibrium reconstruction combining external magnetic measurements with internal diagnostics such as motional Stark effect or polarimetry to resolve the $q$-profile shape. In conventional H-mode plasmas with monotonically increasing $q$-profiles, $q_{\min}$ lies near the magnetic axis and this coordinate approaches 0; in reversed-shear advanced-tokamak scenarios it is off-axis with values in the range 0.3–0.7. The analogous poloidal-flux-based label for the same surface is given by [normalized_poloidal_flux_coordinate_at_minimum_safety_factor](name:normalized_poloidal_flux_coordinate_at_minimum_safety_factor), while the corresponding location for the $q = 1$ sawtooth inversion surface is [normalized_toroidal_flux_coordinate_at_sawtooth_inversion_radius](name:normalized_toroidal_flux_coordinate_at_sawtooth_inversion_radius).

Sign convention: Positive when the toroidal magnetic flux enclosed within the minimum safety factor surface has the same sign as the boundary toroidal flux, which holds for all physically realizable nested-flux-surface equilibria.

---

## REMAINING HUMAN DECISIONS

1. **`safety_factor_at_plasma_boundary` has NULL documentation** (name_stage=accepted, valid).
   It is a q-family member with no body at all — outside rows 15/16 scope but surfaced here.
   **Recommended default:** hand to the docs-generation pipeline (`sn run --only docs` / `sn edit --hint`)
   to author a body consistent with the corrected COCOS=11 sign wording; do not ship an accepted q-name with empty docs.

2. **Whether to also touch names 3–5 for wording uniformity.** They are already COCOS-correct
   (pitch dφ/dθ>0 and flux-increment forms). **Recommended default: leave them.** Editing correct text
   only to unify phrasing risks review churn for no physics gain. Rows 15/16 do not require it.

3. **Explicit "COCOS=11" token in ISN prose.** DD v4.0.0 moved "IMAS uses COCOS=11:" out of the q prose
   into q_like metadata. The corrected sentences above keep an explicit "(COCOS=11)" tag for reader clarity.
   If ISN policy is to keep prose convention-neutral (carrying COCOS only in metadata), drop the parenthetical
   "(COCOS=11)" and keep the relative-alignment statement. **Recommended default: keep the tag** — ISN has no
   separate COCOS metadata channel, so the convention must live in the prose to be unambiguous.
