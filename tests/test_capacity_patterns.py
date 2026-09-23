import unittest

from print_strength_engine.capacity import capacity_for_candidate


class CapacityPatterns(unittest.TestCase):
    def capacity(self, pattern):
        return capacity_for_candidate(
            {'min_section_area_mm2': 100., 'thickness_proxy_mm': 10.,
             'section_normal_axis': 'Z'},
            {'Z': 10.},
            {'configuration': {'sparse_infill_density': '25%',
                               'sparse_infill_pattern': pattern,
                               'wall_loops': 2, 'nozzle_diameter': .4}},
        )

    def test_slicer_spellings_produce_the_same_capacity(self):
        for canonical, aliases in (
            ('zigzag', ('zig-zag', 'Zig Zag', 'zig_zag')),
            ('adaptive', ('adaptivecubic', 'adaptive-cubic', 'Adaptive Cubic')),
            ('tri-hexagon', ('trihexagon', 'tri_hexagon', 'Tri Hexagon')),
            ('line', ('lines',)),
        ):
            for alias in aliases:
                with self.subTest(pattern=alias):
                    self.assertAlmostEqual(self.capacity(alias)['axial_capacity_n'],
                                           self.capacity(canonical)['axial_capacity_n'])

    def test_unknown_patterns_report_fallback_without_substring_matching(self):
        for pattern in ('tpmsd', 'crosshatch', 'future-grid-pattern', None):
            with self.subTest(pattern=pattern):
                value = self.capacity(pattern)
                reason = value['section_knockdown_reasons'][0]
                self.assertEqual(reason['pattern_efficiency'], .85)
                self.assertIs(reason.get('pattern_efficiency_fallback'), True)
                self.assertIsNone(reason['pattern_efficiency_key'])
                self.assertEqual(reason['pattern'], pattern)

    def test_known_pattern_reports_coefficient_source(self):
        reason = self.capacity('adaptivecubic')['section_knockdown_reasons'][0]
        self.assertEqual(reason['pattern_efficiency'], .8)
        self.assertEqual(reason['pattern_efficiency_key'], 'adaptive')
        self.assertFalse(reason['pattern_efficiency_fallback'])

    def test_aligned_rectilinear_preserves_family_assumption(self):
        for pattern in ('alignedrectilinear', 'aligned rectilinear', 'aligned-rectilinear'):
            with self.subTest(pattern=pattern):
                result = self.capacity(pattern)
                self.assertAlmostEqual(result['axial_capacity_n'],
                                       self.capacity('rectilinear')['axial_capacity_n'])
                reason = result['section_knockdown_reasons'][0]
                self.assertEqual(reason['pattern_efficiency_key'], 'rectilinear')
                self.assertEqual(reason['pattern_efficiency_basis'],
                                 'ASSUMED_PATTERN_FAMILY_NOT_CALIBRATED')


if __name__ == '__main__':
    unittest.main()
