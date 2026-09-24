import unittest
import numpy as np
from print_strength_engine.local_thickness import section_metrics, screen_solid


class SectionRegressions(unittest.TestCase):
    def test_disconnected_neighbor_does_not_add_section_material(self):
        solid=np.zeros((5,30,10),bool);solid[0,:,:]=True
        part=np.argwhere(solid)
        before=section_metrics(solid,part,1.,2.4,axis=1)
        solid[3,:,:]=True
        after=section_metrics(solid,part,1.,2.4,axis=1)
        self.assertEqual(after['min_section_area_mm2'],before['min_section_area_mm2'])
        self.assertEqual(after['section_modulus_mm3'],before['section_modulus_mm3'])

    def test_axial_and_bending_minima_have_separate_stations(self):
        solid=np.zeros((4,30,20),bool)
        solid[:4,:15,:4]=True;solid[:1,15:,:20]=True
        result=section_metrics(solid,np.argwhere(solid),1.,2.4,axis=1)
        self.assertEqual(result['min_section_area_mm2'],16.)
        self.assertAlmostEqual(result['section_modulus_mm3'],20/6,delta=.00005)
        self.assertEqual(result['section_station_mm'],.5)
        self.assertEqual(result['bending_section_station_mm'],15.5)
        self.assertEqual(result['bending_section_area_mm2'],20.)

    def test_rotated_section_includes_product_of_inertia(self):
        z,x=np.indices((20,20));plane=abs(z-x)<=1
        solid=np.repeat(plane[:,None,:],30,axis=1)
        result=section_metrics(solid,np.argwhere(solid),1.,2.4,axis=1)
        # 58 finite unit cells: normal +/- (1,-1)/sqrt(2), I=143/6,
        # outer fiber sqrt(2); hence Z=143/(6*sqrt(2)).
        self.assertAlmostEqual(result['section_modulus_mm3'],143/(6*np.sqrt(2)),delta=.00005)

    def test_rectangular_voxel_cells_include_their_own_inertia_and_boundary(self):
        for thickness in (1, 2, 5):
            with self.subTest(thickness=thickness):
                solid = np.ones((thickness, 30, 20), dtype=bool)
                section = section_metrics(solid, np.argwhere(solid), .4, 2.4, axis=1)
                self.assertAlmostEqual(section['section_modulus_mm3'],
                                       8 * (thickness * .4)**2 / 6, delta=.00005)

    def test_selected_station_is_in_world_coordinates(self):
        solid = np.zeros((10, 100, 30), dtype=bool)
        solid[4:7, 5:95, 5:25] = True
        first = screen_solid(solid, [0, 0, 0], .4)['candidates']
        shifted = screen_solid(solid, [100, 200, 300], .4)['candidates']
        self.assertTrue(first)
        self.assertEqual(len(first), len(shifted))
        for a, b in zip(first, shifted):
            axis = 'XYZ'.index(a['section_normal_axis'])
            self.assertAlmostEqual(b['section_station_mm'] - a['section_station_mm'],
                                   [100, 200, 300][axis])
            self.assertEqual(a['position_mm'][axis], a['section_station_mm'])
            self.assertEqual(b['position_mm'][axis], b['section_station_mm'])
            self.assertAlmostEqual(b['bending_section_station_mm']-a['bending_section_station_mm'],
                                   [100,200,300][axis])


if __name__ == '__main__':
    unittest.main()
