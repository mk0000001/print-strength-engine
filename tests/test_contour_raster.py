import unittest
from unittest.mock import patch
import numpy as np
import shapely
from print_strength_engine.local_thickness import screen_contour_layers


class ContourRaster(unittest.TestCase):
    def test_holes_open_lines_and_repaired_rings_preserve_full_grid_mask(self):
        from shapely.geometry import Polygon, LineString
        runs = [
            {'points': [[0,0],[8,0],[8,8],[0,8],[0,0]], 'width_mm': .4},
            {'points': [[2,2],[6,2],[6,6],[2,6],[2,2]], 'width_mm': .4},
            {'points': [[-1,9],[10,9]], 'width_mm': .6},
            {'points': [[12,0],[16,4],[12,4],[16,0],[16,8],[12,0]], 'width_mm': .4},
        ]
        captured = {}
        def capture(solid, origin, spacing):
            captured.update(solid=solid.copy(), origin=origin, spacing=spacing)
            return {'candidates': []}
        with patch('print_strength_engine.local_thickness.screen_solid', capture):
            screen_contour_layers([{'runs': runs, 'z_mm': .4, 'height_mm': .4, 'layer_number': 1}],
                                  [[-1.5,16.5],[-.5,9.5],[0,.4]])
        solid=captured['solid']; origin=captured['origin']; spacing=captured['spacing']
        xx,yy=np.meshgrid(origin[0]+(np.arange(solid.shape[2])+.5)*spacing,
                         origin[1]+(np.arange(solid.shape[1])+.5)*spacing)
        # Independent full-plane raster oracle exercises strict contains boundary semantics.
        parity=np.zeros(xx.shape,dtype=bool);walls=np.zeros_like(parity)
        for run in runs:
            points=run['points'];width=run['width_mm']
            if points[0]==points[-1]:
                polygon=Polygon(points)
                if not polygon.is_valid:polygon=shapely.make_valid(polygon)
                parity ^= shapely.contains_xy(polygon,xx,yy)
            walls |= shapely.contains_xy(LineString(points).buffer(width/2,cap_style=2,join_style=2),xx,yy)
        np.testing.assert_array_equal(solid[3],parity|walls)
        self.assertEqual(int(solid.sum()),int((parity|walls).sum()))

    def test_small_contours_do_not_query_entire_build_plane(self):
        # Distant small islands must not each scan the large empty build plate.
        runs = [{'points': [[x, 0], [x+2, 0], [x+2, 2], [x, 2], [x, 0]],
                 'width_mm': .4} for x in (0, 90)]
        calls = []
        original = shapely.contains_xy
        def measured(geometry, x, y):
            calls.append(np.broadcast_arrays(x, y)[0].size)
            return original(geometry, x, y)
        with patch.object(shapely, 'contains_xy', measured):
            result = screen_contour_layers(
                [{'runs': runs, 'z_mm': .4, 'height_mm': .4, 'layer_number': 1}],
                [[-.2, 92.2], [-.2, 2.2], [0, .4]])
        self.assertGreater(result['occupied_voxels'], 0)
        self.assertLess(max(calls), 150)

    def test_cancel_is_checked_within_a_complex_layer(self):
        calls = 0
        def cancelled():
            nonlocal calls
            calls += 1
            return calls > 1
        runs = [{'points': [[0, 0], [2, 0]], 'width_mm': .4}] * 100
        with self.assertRaisesRegex(RuntimeError, 'ANALYSIS_CANCELLED'):
            screen_contour_layers([{'runs': runs, 'z_mm': .4, 'layer_number': 1}],
                                  [[-.2, 2.2], [-.2, .2], [0, .4]], cancelled=cancelled)
