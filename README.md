# Print Strength Engine

Experimental independent net-section strength screening. Finds the section with the highest local failure index under a specified tensile force and bending moment. Input: reconstructed sections (mm², mm³) and validated allowable stress (MPa). Output: governing section and proportional load multiplier.

This initial core does not yet reconstruct sections from G-code. It must not be presented as a validated whole-part strength predictor. No accuracy guarantee, fatigue, buckling, stress concentration or delamination model is provided. Integration and toolpath reconstruction are in progress.
