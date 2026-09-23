import unittest
from print_strength_engine.infill import infill_response

class InfillTests(unittest.TestCase):
    def test_interpolated_ratio_and_reference_comparison(self):
        result=infill_response('PLA',15,reference_mpa=29.75,pattern='gyroid',walls=3)
        self.assertAlmostEqual(result['relative_strength_ratio'],19.5/34)
        self.assertAlmostEqual(result['comparison_mpa'],29.75*19.5/34)
        self.assertIsNone(result['z_correction'])
        self.assertFalse(result['apply_to_material_area'])
        self.assertFalse(result['calibrated_to_current_part'])
    def test_reference_density_is_identity(self):
        self.assertEqual(infill_response('PLA',100,reference_mpa=35)['comparison_mpa'],35)
    def test_no_cross_material_or_unbounded_extrapolation(self):
        self.assertEqual(infill_response('ABS',45)['status'],'NO_MATCHING_STUDY')
        self.assertEqual(infill_response('PLA',5)['status'],'OUTSIDE_STUDY_RANGE')
        with self.assertRaises(ValueError):infill_response('PLA',float('nan'))

if __name__=='__main__':unittest.main()
