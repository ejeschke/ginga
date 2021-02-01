
import numpy as np

from ginga import trcalc


class TestTrcalc:

    def _2ddata(self):
        data = np.zeros((10, 10), dtype=int)
        for i in range(10):
            for j in range(10):
                data[i, j] = min(i, j)
        return data

    def _3ddata(self):
        data = np.zeros((10, 10, 10), dtype=int)
        for i in range(10):
            for j in range(10):
                for k in range(10):
                    data[i, j, k] = min(i, j, k)
        return data

    def test_get_scaled_cutout_wdht_view(self):

        data = self._2ddata()
        p1 = (2, 2)
        p2 = (4, 4)
        nd = (8, 10)

        res = np.asarray([[2, 2, 2, 2, 2, 2, 2, 2],
                          [2, 2, 2, 2, 2, 2, 2, 2],
                          [2, 2, 2, 2, 2, 2, 2, 2],
                          [2, 2, 2, 2, 2, 2, 2, 2],
                          [2, 2, 2, 3, 3, 3, 3, 3],
                          [2, 2, 2, 3, 3, 3, 3, 3],
                          [2, 2, 2, 3, 3, 3, 3, 3],
                          [2, 2, 2, 3, 3, 3, 4, 4],
                          [2, 2, 2, 3, 3, 3, 4, 4],
                          [2, 2, 2, 3, 3, 3, 4, 4]])

        view, scales = trcalc.get_scaled_cutout_wdht_view(data.shape,
                                                          p1[0], p1[1],
                                                          p2[0], p2[1],
                                                          nd[0], nd[1])
        new_data = data[view]
        assert new_data.shape == (10, 8)
        assert np.allclose(new_data, res)

    def test_get_scaled_cutout_wdhtdp_view(self):

        data = self._3ddata()
        p1 = (0, 0, 0)
        p2 = (9, 9, 9)
        nd = (4, 4, 4)

        res = np.asarray([[[0, 0, 0, 0],
                           [0, 0, 0, 0],
                           [0, 0, 0, 0],
                           [0, 0, 0, 0]],

                          [[0, 0, 0, 0],
                           [0, 2, 2, 2],
                           [0, 2, 2, 2],
                           [0, 2, 2, 2]],

                          [[0, 0, 0, 0],
                           [0, 2, 2, 2],
                           [0, 2, 5, 5],
                           [0, 2, 5, 5]],

                          [[0, 0, 0, 0],
                           [0, 2, 2, 2],
                           [0, 2, 5, 5],
                           [0, 2, 5, 7]]])

        view, scales = trcalc.get_scaled_cutout_wdhtdp_view(data.shape,
                                                            p1, p2, nd)
        new_data = data[view]
        assert new_data.shape == (4, 4, 4)
        assert np.allclose(new_data, res)
