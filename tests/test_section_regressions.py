import unittest
import numpy as np
from print_strength_engine.local_thickness import section_metrics, screen_solid


class SectionRegressions(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
