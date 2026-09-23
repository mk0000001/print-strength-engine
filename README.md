# Print Strength Engine

Experimental independent net-section strength screening. Finds the section with the highest local failure index under a specified tensile force and bending moment. Input: reconstructed sections (mm², mm³) and validated allowable stress (MPa). Output: governing section and proportional load multiplier.

`local_thickness.screen_contour_layers` accepts outer-wall contour layers reconstructed by a host application. It rasterizes their envelopes, excludes support paths supplied separately, and identifies thin-region candidates with section proxies. Raster work is cropped to each contour's bounds without changing the grid. NumPy, SciPy and Shapely 2 are required for geometry screening.

`process` reads deposition settings; `capacity` combines a section proxy and supplied material reference with sparse-core/wall assumptions and optional bending lever. Pattern aliases are normalized and unsupported pattern coefficients are explicitly marked as fallbacks. Speed, layer-height, notch and pattern coefficients are engineering assumptions, not calibrated coupon corrections. A fleet's typical settings are not material calibration data. Layer-summed extrusion areas are comparison proxies and never produce a breaking force.

This must not be presented as a validated whole-part strength predictor. Actual load direction, restraints, local stress concentrations, fatigue, buckling and delamination are not solved. Force estimates depend on the supplied stress and assumed lever; qualitative reports of easy breakage do not validate their numerical accuracy.

Run `python -m unittest discover -s tests` after installing NumPy, SciPy and Shapely.
