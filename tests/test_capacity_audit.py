import unittest
from print_strength_engine.capacity import capacity_for_candidate, VERSION
from print_strength_engine.process import settings


class CapacityAudit(unittest.TestCase):
    candidate={'min_section_area_mm2':100.,'thickness_proxy_mm':10.,
               'section_modulus_mm3':1000/6,'section_normal_axis':'Z'}

    def calculate(self, infill=15, walls=2, pattern='grid'):
        return capacity_for_candidate(self.candidate,{'Z':10.},
            {'configuration':{'sparse_infill_density':infill,'wall_loops':walls,
                              'line_width':.4,'sparse_infill_pattern':pattern}},10.)

    def test_zero_settings_are_not_replaced_with_defaults(self):
        read=settings({'configuration':{'sparse_infill_density':0,'fill_density':50,
                                        'wall_loops':0,'perimeters':4}})
        self.assertEqual(read['infill_percent'],0)
        self.assertEqual(read['walls'],0)
        self.assertEqual(self.calculate(0,0)['axial_capacity_n'],0.)

    def test_actual_line_width_takes_precedence_over_nozzle(self):
        read=settings({'configuration':{'line_width':.8,'nozzle_diameter':.4}})
        self.assertEqual(read['line_width_mm'],.8)
        self.assertEqual(read['line_width_source'],'GCODE_LINE_WIDTH')

    def test_auto_width_does_not_hide_valid_configured_width(self):
        for auto in (0,'0','auto','120%'):
            read=settings({'configuration':{'outer_wall_line_width':auto,'line_width':.8,'nozzle_diameter':.4}})
            self.assertEqual(read['line_width_mm'],.8)
            self.assertEqual(read['line_width_source'],'GCODE_LINE_WIDTH')

    def test_more_walls_do_not_reduce_same_section_axial_scenario(self):
        values=[self.calculate(walls=n)['axial_capacity_n'] for n in (0,1,2,3,4)]
        self.assertEqual(values,sorted(values))

    def test_full_density_is_not_penalized_by_pattern_name(self):
        values=[self.calculate(100,pattern=p)['axial_capacity_n'] for p in ('grid','gyroid','lightning')]
        self.assertEqual(values,[1000.]*3)

    def test_sparse_area_factor_is_not_applied_to_bending_inertia(self):
        result=self.calculate()
        self.assertIsNotNone(result['axial_capacity_n'])
        self.assertIsNone(result['bending_capacity_nmm'])
        self.assertIsNone(result['governing_capacity_n'])
        self.assertFalse(result['is_failure_prediction'])
        self.assertEqual(result['model_version'],VERSION)

    def test_unknown_structure_does_not_mean_solid(self):
        result=capacity_for_candidate(self.candidate,{'Z':10.})
        self.assertIsNone(result['axial_capacity_n'])
        self.assertFalse(result['assumes_solid_section'])

    def test_nominal_solid_section_matches_analytic_units(self):
        result=self.calculate(100)
        self.assertAlmostEqual(result['bending_capacity_nmm'],10000/6)
        self.assertAlmostEqual(result['bending_force_n'],1000/6)

    def test_full_infill_does_not_establish_contact_or_void_geometry(self):
        result=self.calculate(100)
        self.assertEqual(result['section_geometry_status'],'OUTER_ENVELOPE_ONLY')
        self.assertIsNone(result['effective_load_bearing_area_mm2'])
        self.assertIsNone(result['bonded_contact_area_mm2'])
        self.assertFalse(result['solid_section_verified'])
        self.assertIn('VOID_AND_CONTACT_GEOMETRY_UNKNOWN',result['assessment_gaps'])
        self.assertIn('NOTCH_AND_CRACK_FAILURE_NOT_SOLVED',result['assessment_gaps'])

    def test_contact_normalized_stress_cannot_multiply_outer_envelope(self):
        for basis in ('INTERLAYER_CONTACT','NET_MATERIAL'):
            result=capacity_for_candidate(self.candidate,{'Z':10.},
                {'configuration':{'sparse_infill_density':100}},10.,reference_area_basis=basis)
            self.assertEqual(result['calculation_status'],'INCOMPATIBLE_STRESS_AREA_BASIS')
            for key in ('axial_capacity_n','bending_force_n','governing_capacity_n'):
                self.assertIsNone(result[key])

    def test_layer_summed_extrusion_never_becomes_a_failure_load(self):
        result=capacity_for_candidate({'material_area_proxy_mm2':100.,'axis':'Z'},
                                      {'Z':10.},{'configuration':{'sparse_infill_density':100}},10.)
        for key in ('axial_capacity_n','bending_force_n','governing_capacity_n'):
            self.assertIsNone(result[key])
        self.assertEqual(result['governing_mode'],'LAYER_COMPARISON_ONLY')
        self.assertIsNone(result['allowable_mpa'])
        self.assertEqual(result['material_reference_mpa'],10.)
        self.assertEqual(result['section_knockdown_reasons'],[])

    def test_scenario_never_claims_validated_transfer_or_confidence_interval(self):
        result=self.calculate()
        self.assertFalse(result['empirically_validated'])
        self.assertFalse(result['validation']['process_transfer_validated'])
        self.assertFalse(result['validation']['source_grade_transfer_validated'])
        self.assertIsNone(result['prediction_interval_n'])
        self.assertEqual(result['material_reference_mpa'],10.)
        self.assertFalse(result['section_knockdown_reasons'][0]['empirically_validated'])


if __name__=='__main__':unittest.main()
