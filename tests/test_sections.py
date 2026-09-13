import unittest
from print_strength_engine import weakest_section, weakest_layer_candidate

class Sections(unittest.TestCase):
    def test_neck_controls(self):
        result=weakest_section([{'id':'body','area_mm2':20,'allowable_mpa':10},
                               {'id':'neck','area_mm2':5,'allowable_mpa':10}],10)
        self.assertEqual(result['weakest_section']['section_id'],'neck')
        self.assertEqual(result['capacity_at_proportional_loading_n'],50)
    def test_weak_material_can_control_larger_section(self):
        r=weakest_section([{'id':'a','area_mm2':20,'allowable_mpa':1},
                           {'id':'b','area_mm2':5,'allowable_mpa':10}],10)
        self.assertEqual(r['weakest_section']['section_id'],'a')
    def test_bending(self):
        r=weakest_section([{'id':'a','area_mm2':10,'allowable_mpa':10,'section_modulus_mm3':2}],10,18)
        self.assertEqual(r['weakest_section']['failure_index'],1)
    def test_invalid(self):
        with self.assertRaises(ValueError): weakest_section([],1)
    def test_layer_neck_candidate(self):
        volumes=[20,20,20,3,20,20,20,20]
        profile={'layers':[{'z_mm':i*.2,'volume_mm3':v} for i,v in enumerate(volumes)]}
        result=weakest_layer_candidate(profile)
        self.assertEqual(result['status'],'GEOMETRIC_CANDIDATE_ONLY')
        self.assertAlmostEqual(result['weakest_section']['z_mm'],.6)
        self.assertAlmostEqual(result['weakest_section']['material_area_proxy_mm2'],15)

if __name__=='__main__': unittest.main()
