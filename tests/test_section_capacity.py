import unittest
import numpy as np
from print_strength_engine.local_thickness import screen_solid
from print_strength_engine.capacity import capacity_for_candidate


class SectionCapacity(unittest.TestCase):
    def plate(self):
        solid=np.zeros((40,100,30),dtype=bool)
        # 2 mm thick (5 voxels), 12 mm wide (30 voxels), long in Y.
        solid[18:23,5:95,5:35 if False else 5:35]=True
        return solid

    def test_minimum_section_matches_plate_thickness_times_width(self):
        solid=np.zeros((40,100,35),dtype=bool);solid[18:23,5:95,5:35]=True
        result=screen_solid(solid,[0,0,0],.4)
        best=result['candidates'][0]
        self.assertEqual(best['section_normal_axis'],'Y')
        self.assertAlmostEqual(best['min_section_area_mm2'],5*30*.16,delta=.16*30)
        self.assertGreater(best['section_modulus_mm3'],0)

    def test_capacity_uses_axis_specific_allowable_and_reports_both_units(self):
        candidate={'min_section_area_mm2':60.,'section_modulus_mm3':20.,'section_normal_axis':'Z'}
        value=capacity_for_candidate(candidate,{'X':'35.9','Y':'35.9','Z':'14.42'},
                                     {'configuration':{'sparse_infill_density':100}})
        self.assertEqual(value['allowable_mpa'],14.42)
        self.assertAlmostEqual(value['axial_capacity_n'],60*14.42,places=6)
        self.assertAlmostEqual(value['axial_capacity_kgf'],60*14.42/9.80665,places=6)
        self.assertAlmostEqual(value['bending_capacity_nmm'],20*14.42,places=6)
        self.assertFalse(value['is_measured'])
        self.assertEqual(value['basis'],'SOLID_ENVELOPE_SECTION_TIMES_MATERIAL_REFERENCE')

    def test_capacity_is_withheld_without_section_or_material(self):
        self.assertIsNone(capacity_for_candidate({'min_section_area_mm2':None},{'Z':'10'}))
        self.assertIsNone(capacity_for_candidate({'min_section_area_mm2':60.,'section_normal_axis':'Z'},None))
        self.assertIsNone(capacity_for_candidate({'min_section_area_mm2':60.,'section_normal_axis':'Z'},{'Z':'0'}))


if __name__=='__main__':unittest.main()
