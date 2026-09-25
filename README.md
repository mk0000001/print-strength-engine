# Print Strength Engine

Release: **v0.11.0** · 11 recorded code revisions (10 updates after initial import). [Commit ledger](VERSION_HISTORY.json).

Count includes reachable non-merge commits touching the engine package, including merged development history; excludes documentation-only, tests-only, host-app changes and generated _version.py. It counts commits, not individual features or validated accuracy. Version convention: 0.<code revision count>.<release metadata fix>. Past results without a recorded version remain unknown.


Public documentation: [research evidence and sources](docs/research-evidence.md) · [system validation and limitations](docs/system-validation.md) · [process API](PROCESS_EVIDENCE.md).

Current contracts are `GCODE_PROCESS_EVIDENCE_V3_THERMAL_CONTEXT` and `CAPACITY_SCENARIO_V4_GEOMETRY_QUALIFIED`. Material references, geometric screening and hypothetical load scenarios are separate outputs; none is a calibrated whole-part failure prediction.

`weakest_layer_candidate(profile)` now returns up to six separated internal constriction candidates in `weak_candidates`; `weakest_section` is the first ranked candidate. It compares the model volume/height area proxy against the median on **both** sides at two neighborhood sizes. Uniform sections and monotonic tapers do not automatically produce a candidate. Terminal features with less than 2% of model volume above them are excluded; this is a relevance heuristic, not a load estimate. Nearby candidates are suppressed into one region. The minimum narrowing threshold (2%), neighborhood sizes and separation are transparent screening assumptions, not empirically validated fracture thresholds. Mild changes are explicitly labeled. Without loads, restraints, connected sections, material bonding and stress concentrations, the ranking is **not** an actual weakest-point or failure-load prediction. Candidate markers locate Z layers, not resolved XY fracture points.

`print_strength_engine.infill.infill_response()` provides a PLA literature comparison over 10–100% infill using within-study piecewise interpolation from [Ben Amor et al. (2024), Table 6](https://doi.org/10.35219/awet.2024.10). It does not assert matching pattern/wall/brand calibration, does not extrapolate outside the study range, and must not be multiplied into the measured material area. Optional `reference_mpa` produces a conditional comparison, not a part capacity; no Z correction is invented.

Experimental independent net-section strength screening. Finds the section with the highest local failure index under a specified tensile force and bending moment. Input: reconstructed sections (mm², mm³) and validated allowable stress (MPa). Output: governing section and proportional load multiplier.

`local_thickness.screen_contour_layers` accepts outer-wall contour layers reconstructed by a host application. It rasterizes their envelopes, excludes support paths supplied separately, and identifies thin-region candidates with section proxies. Raster work is cropped to each contour's bounds without changing the grid. NumPy, SciPy and Shapely 2 are required for geometry screening.

`process` reads deposition settings and preserves reference/target conditions separately. Evidence V2 retires uncalibrated speed/layer multipliers: identity factors are `NOT_APPLIED` placeholders and `effective_mpa` is null. Verified literature observations are comparisons only; tensile and shear properties are not interchangeable and no paper ratio transfers automatically to a part. See [PROCESS_EVIDENCE.md](PROCESS_EVIDENCE.md).

`capacity` combines a section proxy and supplied material reference with explicit, uncalibrated sparse-core/wall assumptions and optional bending lever. Pattern aliases are normalized and unsupported pattern coefficients are marked as fallbacks. Outputs expose calibration status, material reference stress and validation gaps; they provide no prediction interval. A fleet's typical settings are not material calibration data. Layer-summed extrusion areas are comparison proxies and never produce a breaking force or allowable stress.

Geometry schema V4 isolates face-connected material and preserves separate axial-area and principal-bending minima, including finite-cell inertia coupling. `section_station_mm` remains the axial station; `bending_section_station_mm` must be used for a bending scenario. Candidate windows remain cropped geometry screens, not complete load-path solutions.

The current capacity model retains the audit fixes introduced in V2: no uncalibrated wall-count notch penalty; missing structure settings do not imply solid infill; numeric zero settings are preserved. Sparse/unknown infill bending and governing loads are withheld because an area fraction does not establish section inertia. Sparse axial output is an explicitly uncalibrated rectangular shell/core scenario. Nominal 100% scenarios do not receive pattern-name penalties. Hypothetical lever scenarios must not be compared as a common-load failure ranking. All capacities expose `is_failure_prediction: false`.

This must not be presented as a validated whole-part strength predictor. Actual load direction, restraints, local stress concentrations, fatigue, buckling and delamination are not solved. Force estimates depend on the supplied stress and assumed lever; qualitative reports of easy breakage do not validate their numerical accuracy.

Run `python -m unittest discover -s tests` after installing NumPy, SciPy and Shapely.

Process evidence V3 preserves per-tool temperature/flow slots and reports no single temperature for conflicting or incomplete lists. Flow, top/bottom shells and cooling setpoints remain file settings, not observed void fraction or local thermal history. No duration-per-layer approximation is used as local return time.

Capacity V4 separates nominal full infill from verified solid/contact geometry. `reference_area_basis` can be `UNKNOWN`, `GROSS_ENVELOPE`, `NET_MATERIAL` or `INTERLAYER_CONTACT`; the latter two withhold force on an outer-envelope section to prevent mixing stress denominators. Unknown reference basis retains only the existing uncalibrated scenario, never a validated prediction. This API does not reconstruct bonded area, solve cracks/notches, or calibrate a universal void/healing factor.
