# Print Strength Engine

`print_strength_engine.infill.infill_response()` provides a PLA literature comparison over 10–100% infill using within-study piecewise interpolation from [Ben Amor et al. (2024), Table 6](https://doi.org/10.35219/awet.2024.10). It does not assert matching pattern/wall/brand calibration, does not extrapolate outside the study range, and must not be multiplied into the measured material area. Optional `reference_mpa` produces a conditional comparison, not a part capacity; no Z correction is invented.

Experimental independent net-section strength screening. Finds the section with the highest local failure index under a specified tensile force and bending moment. Input: reconstructed sections (mm², mm³) and validated allowable stress (MPa). Output: governing section and proportional load multiplier.

This initial core does not yet reconstruct sections from G-code. It must not be presented as a validated whole-part strength predictor. No accuracy guarantee, fatigue, buckling, stress concentration or delamination model is provided. Integration and toolpath reconstruction are in progress.
