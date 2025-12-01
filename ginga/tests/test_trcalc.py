import hashlib
import numpy as np

from ginga import trcalc


class TestTrcalc:

    def _2ddata(self, shape, data_np=None):
        if data_np is None:
            data_np = np.asarray([min(i, j)
                                  for i in range(shape[0])
                                  for j in range(shape[1])])
        data_np = data_np.reshape(shape)
        return data_np

    def _3ddata(self, shape, data_np=None):
        if data_np is None:
            data_np = np.asarray([min(i, j, k)
                                  for i in range(shape[0])
                                  for j in range(shape[1])
                                  for k in range(shape[2])])
        data_np = data_np.reshape(shape)
        return data_np

    def test_get_scaled_cutout_wdht_view(self):

        data = self._2ddata((10, 10))
        p1 = (2, 2)
        p2 = (4, 4)
        nd = (8, 10)

        view, scales = trcalc.get_scaled_cutout_wdht_view(data.shape,
                                                          p1[0], p1[1],
                                                          p2[0], p2[1],
                                                          nd[0], nd[1])
        new_data = trcalc.fancy_index(data, view)
        assert new_data.shape == (10, 8)
        assert isinstance(new_data[0, 0], np.integer)
        res = 'dc025d4e14db5529c581cbe24f0616721bb33f63aabcfcc0d432edf00d8cdc2d'
        m = hashlib.sha256()
        m.update(str(new_data.tolist()).encode())
        assert m.hexdigest() == res

    def test_get_scaled_cutout_wdhtdp_view(self):

        data = self._3ddata((10, 10, 10))
        p1 = (0, 0, 0)
        p2 = (9, 9, 9)
        nd = (4, 4, 4)

        view, scales = trcalc.get_scaled_cutout_wdhtdp_view(data.shape,
                                                            p1, p2, nd)
        new_data = trcalc.fancy_index(data, view)
        assert new_data.shape == (4, 4, 4)
        assert isinstance(new_data[0, 0, 0], np.integer)
        res = 'c01c00af06fb2dc5c8cd6cf96927ba6ddd8d2caba3fc33074c9eaab5cc0ac498'
        m = hashlib.sha256()
        m.update(str(new_data.tolist()).encode())
        assert m.hexdigest() == res
