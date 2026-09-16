import unittest
import numpy as np
from print_strength_engine.local_thickness import screen_solid


class LocalThickness(unittest.TestCase):
    def test_thin_finished_part_detected_without_z_neck(self):
        solid=np.zeros((50,80,20),dtype=bool)
        solid[2:48,2:78,8:11]=True
        result=screen_solid(solid,[0,0,0],.4)
        self.assertEqual(result['status'],'THIN_REGIONS_FOUND')
        self.assertTrue(result['candidates'])
        self.assertTrue(all(c['thickness_proxy_mm']<=2.4 for c in result['candidates']))

    def test_thick_block_surfaces_are_not_falsely_thin(self):
        solid=np.zeros((45,45,45),dtype=bool);solid[2:43,2:43,2:43]=True
        result=screen_solid(solid,[0,0,0],.4)
        self.assertEqual(result['candidates'],[])

    def test_thin_connector_is_located_outside_thick_block(self):
        solid=np.zeros((30,40,90),dtype=bool)
        solid[2:27,2:37,2:32]=True;solid[12:15,17:22,30:85]=True
        result=screen_solid(solid,[0,0,0],.4)
        self.assertTrue(any(c['position_mm'][0]>14 for c in result['candidates']))
        self.assertTrue(all(c['load_capacity_n'] is None for c in result['candidates']))


if __name__=='__main__':unittest.main()
