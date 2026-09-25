import importlib.util
import unittest

from print_strength_engine.process import material_factors, process_adjustment, settings


class ProcessEvidence(unittest.TestCase):
    def test_unknown_process_never_becomes_a_corrected_strength(self):
        for analysis in ({}, {'configuration': {'layer_height': .4},
                              'process_metrics': {'commanded_speed_mm_s': {'p50_approx': 800}}}):
            result = process_adjustment(analysis, {'X': '50', 'Y': '50', 'Z': '30'})
            self.assertIsNone(result['effective_mpa'])
            self.assertEqual(result['status'], 'UNCALIBRATED_PROCESS_MODEL')
            self.assertFalse(result['adjusted'])
            self.assertEqual(result['reference_mpa'], {'X': '50', 'Y': '50', 'Z': '30'})
            self.assertEqual(result['factor_status'], 'NOT_APPLIED')
            self.assertEqual(result['factors'], {'X': 1., 'Y': 1., 'Z': 1.})

    def test_identity_is_not_a_physical_prediction(self):
        result = material_factors({'configuration': {'layer_height': .1}})
        self.assertFalse(result.get('is_prediction', True))
        self.assertEqual(result['applied'], [])

    def test_preserves_source_target_context_and_zero_settings(self):
        analysis = {'configuration': {'filament_type': 'PLA', 'filament_grade': 'Other PLA',
                    'bed_temperature': 0, 'chamber_temperature': 0, 'fan_speed': 0,
                    'moisture_condition': 'unknown', 'annealing': 'none', 'nozzle_temperature': 210}}
        read = settings(analysis)
        self.assertEqual(read.get('bed_c'), 0)
        self.assertEqual(read.get('chamber_c'), 0)
        self.assertEqual(read.get('fan_percent'), 0)
        self.assertEqual(read.get('material_grade'), 'Other PLA')
        result = process_adjustment(analysis, {'X': 50, 'Y': 50, 'Z': 30},
                                    reference_context={'material_grade': 'Reference PLA', 'layer_height_mm': .2})
        self.assertEqual(result['reference_context']['material_grade'], 'Reference PLA')
        self.assertEqual(result['target_context']['material_grade'], 'Other PLA')
        self.assertEqual(result['target_context']['moisture_condition'], 'unknown')

    def evidence(self, *args, **kwargs):
        self.assertIsNotNone(importlib.util.find_spec('print_strength_engine.evidence'))
        from print_strength_engine.evidence import literature_comparisons
        return literature_comparisons(*args, **kwargs)

    def test_generic_pla_observations_are_not_grade_matches_or_adjustments(self):
        rows = self.evidence({'material_family': 'PLA', 'layer_height_mm': .2, 'nozzle_c': 220})
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['material_match'], 'SAME_FAMILY_NOT_GRADE_MATCH')
        self.assertEqual(row['observations'][0]['value_mpa'], 32.15)
        self.assertEqual(row['observations'][0]['value_kind'], 'DERIVED_FROM_REPORTED_VALUES')
        self.assertEqual(row['observations'][1]['value_mpa'], 30.07)
        self.assertAlmostEqual(row['observed_ratio'], .9353032659409021)
        self.assertFalse(row['applied'])
        self.assertIsNone(row['transfer_factor'])
        self.assertIn('nozzle_c', [x['field'] for x in row['condition_mismatches']])
        self.assertEqual(row['target_context']['nozzle_c'], 220)

    def test_shear_cannot_enter_tensile_comparisons(self):
        self.assertEqual(self.evidence({'material_family': 'ABS'}), [])
        rows = self.evidence({'material_family': 'ABS'}, property_name='interlayer_shear_strength')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['observations'][0]['value_mpa'], 23.01)
        self.assertEqual(rows[0]['property'], 'interlayer_shear_strength')
        self.assertIsNone(rows[0]['transfer_factor'])

    def test_orientation_observations_do_not_claim_significant_difference(self):
        row = self.evidence({'material_family': 'PEI', 'material_grade': 'ULTEM 9085'})[0]
        self.assertEqual([x['value_mpa'] for x in row['observations']], [65.9, 73.0])
        self.assertEqual(row['statistical_comparison'], 'SAME_TUKEY_GROUP')
        self.assertFalse(row['applied'])

    def test_returned_evidence_does_not_mutate_catalog(self):
        row = self.evidence({'material_family': 'PLA'})[0]
        row['observations'][0]['value_mpa'] = -1
        self.assertEqual(self.evidence({'material_family': 'PLA'})[0]['observations'][0]['value_mpa'], 32.15)

    def test_detected_family_and_list_temperatures_preserve_no_grade_claim(self):
        for detected in ('PLA', ['PLA'], ['PLA', 'PLA']):
            read = settings({'detected_materials': detected, 'configuration': {
                'nozzle_temperature': [210, 215], 'bed_temperature': [60],
                'filament_settings_id': 'PrimaSelect PLA PRO'}})
            self.assertEqual(read['material_family'], 'PLA')
            self.assertIsNone(read['nozzle_c'])
            self.assertEqual(read['nozzle_temperatures_c'], [210, 215])
            self.assertEqual(read['bed_c'], 60)
            self.assertIsNone(read['material_grade'])
        self.assertIsNone(settings({'detected_materials': ['PLA', 'ABS']})['material_family'])

    def test_no_ratio_outside_observed_layer_heights(self):
        row = self.evidence({'material_family': 'PLA', 'layer_height_mm': .4})[0]
        self.assertIsNone(row['observed_ratio'])
        self.assertFalse(row['target_within_observed_levels'])
        self.assertEqual(row['applicability'], 'OUTSIDE_OBSERVED_LEVELS')

    def test_thermal_context_does_not_invent_local_measurements(self):
        read = settings({'duration_seconds':1000,'layer_count':100,'configuration':{
            'nozzle_temperature':'210;220','filament_flow_ratio':[1.0,1.1],
            'slow_down_layer_time':8,'top_shell_layers':4,'bottom_shell_layers':3}})
        self.assertIsNone(read['nozzle_c'])
        self.assertEqual(read['nozzle_temperatures_c'],[210,220])
        self.assertIsNone(read['flow_ratio'])
        self.assertEqual(read['flow_ratios'],[1.0,1.1])
        self.assertEqual(read['minimum_layer_time_setting_s'],8)
        self.assertIsNone(read['local_interlayer_return_time_s'])
        self.assertIsNone(read['measured_substrate_temperature_c'])
        self.assertIsNone(read['measured_void_fraction'])
        self.assertEqual(read['top_shell_layers'],4)
        self.assertEqual(read['bottom_shell_layers'],3)

    def test_uniform_temperature_is_known_but_invalid_member_is_not_discarded(self):
        self.assertEqual(settings({'configuration':{'nozzle_temperature':[210,210]}})['nozzle_c'],210)
        self.assertIsNone(settings({'configuration':{'nozzle_temperature':[210,'unknown']}})['nozzle_c'])


if __name__ == '__main__':
    unittest.main()
