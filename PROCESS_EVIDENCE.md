# Process evidence API

Current contract: `process.VERSION = GCODE_PROCESS_EVIDENCE_V3_THERMAL_CONTEXT`. Universal speed and layer-height knockdowns were retired in V2; V3 additionally preserves per-tool thermal/flow context. The audit did not establish calibrated transfers between published reference coupons and target parts. See the [research evidence review](docs/research-evidence.md) for public sources and their limits.

`process_adjustment(analysis, directional_mpa, *, reference_context=None)` retains its two positional arguments and returns:

- `status: UNCALIBRATED_PROCESS_MODEL`, `factor_status: NOT_APPLIED`, `is_prediction: false`.
- `reference_mpa`: supplied X/Y/Z values represented as strings, unchanged numerically.
- `effective_mpa: null`, `adjusted: false`, `applied: []`.
- `factors: {X: 1, Y: 1, Z: 1}` for compatibility only. These are **not** predictions of equal strength at different settings.
- `reference_context`: caller-supplied coupon context or null; `target_context` and `settings`: parsed target information.
- `literature_comparisons`: qualified tensile observations for the detected material family.

Invalid/incomplete directional reference inputs still return null. Consumers must not fall back from missing `effective_mpa` to `reference_mpa` while describing that fallback as an as-printed prediction. A separately labeled reference-material scenario is an application decision, not a calibrated process result.

Target settings retain nozzle/bed/chamber temperatures, fan percentage, grade, moisture and annealing metadata when supplied. Per-tool temperature and flow lists retain their slots, including unknown values. Conflicting or incomplete lists do not become a single representative temperature or multiplier. Minimum-layer-time and fan settings are commands, not measured local return time or bonded contact area. `detected_materials` can supply the family if configuration lacks it. Multiple distinct detected families do not select an arbitrary one. A slicer profile name is not promoted to a verified material grade.

`evidence.literature_comparisons(target_context, property_name='tensile_strength')` returns same-family evidence with source URLs/locators, original conditions, target context, unknown conditions and explicit mismatches. Generic PLA is `SAME_FAMILY_NOT_GRADE_MATCH`; even `EXACT_GRADE_NAME_ONLY` establishes no process transfer. Every result has `applied: false`, `transfer_factor: null` and `is_prediction: false`.

S050 retains 32.15 MPa as a derived unannealed baseline (33.37−1.22), versus reported 30.07 MPa. The ratio is exposed only when the target layer height is one of the observed 0.1/0.2 mm levels; no interpolation or extrapolation occurs. Even at those levels, it is a literature ratio, not a target correction. Axis and replicate dispersion remain unverified. S088 XY/XZ observations retain their same Tukey group; the module does not infer significance from different means. S028 is available only with `property_name='interlayer_shear_strength'` and cannot enter the default tensile list.

The [public research review](docs/research-evidence.md) summarizes the source audit and distinguishes original-source checks, literature replay and experimental comparisons. No exponent, pattern coefficient or arbitrary prior was fitted.

Verification: run `python -m unittest discover -s tests` with NumPy, SciPy and Shapely installed. A passing software test suite does not establish physical prediction accuracy; see [system validation](docs/system-validation.md).
