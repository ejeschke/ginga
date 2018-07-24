
import numpy as np

from ginga import AstroImage, trcalc
from ginga.misc import log


class Test_numpy(object):
    def setup_class(self):
        self.logger = log.get_logger("Test_numpy", null=True)

    def _get_data(self, shape, data_np=None):
        if data_np is None:
            data_np = np.random.randint(0, 10000, shape)
        return data_np.reshape(shape)

    def test_numpy_slice_trcalc(self):
        """Test that we can get a subslice of an array.
        """
        arr_np = self._get_data((1000, 500))

        x_slice, y_slice = slice(12, 499, 3), slice(10, 951, 11)
        view = (y_slice, x_slice)
        data_np = trcalc.fancy_index(arr_np, view)
        assert isinstance(data_np, np.ndarray)
        assert data_np.shape == (86, 163)

    def test_numpy_slice_aimg(self):
        """Test that we can get a subslice of an AstroImage object.
        """
        aimg = AstroImage.AstroImage(logger=self.logger)
        aimg.set_data(self._get_data((700, 800)))

        x_slice, y_slice = slice(12, 800, 8), slice(0, 700, 10)
        view = (y_slice, x_slice)
        data_np = aimg._slice(view)
        assert isinstance(data_np, np.ndarray)
        assert data_np.shape == (70, 99)

    def test_numpy_aimg_get_data_xy(self):
        """Test that we can get a single value from an AstroImage object.
        """
        aimg = AstroImage.AstroImage(logger=self.logger)
        aimg.set_data(self._get_data((5, 5), data_np=np.arange(0, 25)))

        val = int(aimg.get_data_xy(3, 3))
        assert isinstance(val, int)
        assert val == 18

    def test_numpy_fancy_scale(self):
        """Test that we can get a fancy superslice of a numpy array.
        """
        arr_np = self._get_data((5, 5, 5))

        p1 = (0, 0, 0)
        p2 = (5, 5, 5)
        new_dims = (51, 51, 51)

        res, scales = trcalc.get_scaled_cutout_wdhtdp(arr_np, p1, p2,
                                                      new_dims,
                                                      logger=self.logger)
        assert isinstance(res, np.ndarray)
        assert res.shape == new_dims
