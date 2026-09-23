# Strength model scope

This package separates geometry screening from material references and loads.

`weakest_layer_candidate` ranks interior Z interfaces by deposited model filament volume divided by observed layer height. This is a bounded-memory screening proxy, not a topological slice union or load capacity. Without force direction, supports/restraints and real net-section reconstruction, a global weakest part cannot be proven. `weakest_section` accepts independently validated sections, local allowable stress and a specified axial force/bending moment, then returns the first local limit for proportional loading.

The three user-supplied research reports were reviewed as design inputs. Their numerical accuracy claims (±6%, ±10–25%, and 2–5%) are mutually incompatible without matching test fixtures. An arithmetic assertion that cos²45°≈0.707 is incorrect (it is 0.5). Their uncalibrated temperature/healing and pattern coefficients are not silently applied. Independent specimen measurements are required before claiming prediction accuracy.
