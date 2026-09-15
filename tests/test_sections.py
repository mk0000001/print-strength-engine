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
    def test_layer_number_is_preserved_not_rebuilt_from_sorted_position(self):
        rows=[{'z_mm':(i+1)*.2,'volume_mm3':3 if i==3 else 20,
               'layer_number':101+i} for i in range(8)]
        result=weakest_layer_candidate({'layers':list(reversed(rows))})
        self.assertEqual(result['weakest_section']['layer_number'],104)
    def test_missing_layer_marker_does_not_invent_an_ordinal(self):
        rows=[{'z_mm':(i+1)*.2,'volume_mm3':3 if i==3 else 20} for i in range(8)]
        result=weakest_layer_candidate({'layers':rows})
        self.assertIsNone(result['weakest_section']['layer_number'])

if __name__=='__main__': unittest.main()
