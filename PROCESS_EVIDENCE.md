# Process evidence API

`process.VERSION = GCODE_PROCESS_EVIDENCE_V2` retires the universal speed and layer-height knockdowns. The audit did not establish calibrated transfers between published reference coupons and target parts.

`process_adjustment(analysis, directional_mpa, *, reference_context=None)` retains its two positional arguments and returns:

- `status: UNCALIBRATED_PROCESS_MODEL`, `factor_status: NOT_APPLIED`, `is_prediction: false`.
- `reference_mpa`: supplied X/Y/Z values represented as strings, unchanged numerically.
- `effective_mpa: null`, `adjusted: false`, `applied: []`.
- `factors: {X: 1, Y: 1, Z: 1}` for compatibility only. These are **not** predictions of equal strength at different settings.
- `reference_context`: caller-supplied coupon context or null; `target_context` and `settings`: parsed target information.
- `literature_comparisons`: qualified tensile observations for the detected material family.

Invalid/incomplete directional reference inputs still return null. Consumers must not fall back from missing `effective_mpa` to `reference_mpa` while describing that fallback as an as-printed prediction. A separately labeled reference-material scenario is an application decision, not a calibrated process result.

Target settings retain nozzle/bed/chamber temperatures, fan percentage, grade, moisture and annealing metadata when supplied. Selected raw process metadata is retained to preserve lists, ranges and unparsed settings. Numeric list settings use their first element, matching legacy comma-separated behavior; this does not resolve tool-specific temperatures. `detected_materials` can supply the family if configuration lacks it. Multiple distinct detected families do not select an arbitrary one. A slicer profile name is not promoted to a verified material grade.

`evidence.literature_comparisons(target_context, property_name='tensile_strength')` returns same-family evidence with source URLs/locators, original conditions, target context, unknown conditions and explicit mismatches. Generic PLA is `SAME_FAMILY_NOT_GRADE_MATCH`; even `EXACT_GRADE_NAME_ONLY` establishes no process transfer. Every result has `applied: false`, `transfer_factor: null` and `is_prediction: false`.

S050 retains 32.15 MPa as a derived unannealed baseline (33.37−1.22), versus reported 30.07 MPa. The ratio is exposed only when the target layer height is one of the observed 0.1/0.2 mm levels; no interpolation or extrapolation occurs. Even at those levels, it is a literature ratio, not a target correction. Axis and replicate dispersion remain unverified. S088 XY/XZ observations retain their same Tukey group; the module does not infer significance from different means. S028 is available only with `property_name='interlayer_shear_strength'` and cannot enter the default tensile list.

Source audit: `reports/strength-empirical-validation-20260925.md`, `reports/bundle-primary-verified-numeric-20260925.json`, and `reports/bundle-empirical-benchmark-20260925.json` in the parent repository. No exponent, pattern coefficient or arbitrary prior was fitted.

Verification: new contract regressions were run failing before implementation and passing afterward. Full engine unittest discovery was attempted on Windows with `.ops/geomrt;external/print-strength-engine`; geometry tests require the working SciPy/Shapely Docker environment. Capacity and geometry code were not changed by this process/evidence migration.
