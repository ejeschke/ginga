import hashlib
import numpy as np
import pytest

zarr = pytest.importorskip('zarr')

from ginga import AstroImage, trcalc
from ginga.misc import log


class TestZarr:
    def setup_class(self):
        self.logger = log.get_logger("TestZarr", null=True)

    def _getdata(self, shape, data_np=None):
        if data_np is None:
            data_np = np.min(np.indices(shape), axis=0)
        data_np = data_np.reshape(shape)
        data_z = zarr.creation.array(data_np, chunks=10)
        return data_z

    def test_zarr_slice_trcalc(self):
        """Test that we can get a subslice of a zarr.
        """
        arr_z = self._getdata((1000, 500))

        x_slice, y_slice = slice(12, 499, 3), slice(10, 951, 11)
        view = (y_slice, x_slice)
        data_np = trcalc.fancy_index(arr_z, view)
        assert isinstance(data_np, np.ndarray)
        assert data_np.shape == (86, 163)
        assert isinstance(data_np[0, 0], np.integer)
        res = '177e1ed261ea24df277511078631ec0f95dfc3e781ac15b2d200f0f0040282ae'
        m = hashlib.sha256()
        m.update(str(data_np.tolist()).encode())
        assert m.hexdigest() == res

    def test_zarr_slice_aimg(self):
        """Test that we can get a subslice of an AstroImage object.
        """
        aimg = AstroImage.AstroImage(logger=self.logger)
        aimg.set_data(self._getdata((700, 800)))

        x_slice, y_slice = slice(12, 800, 8), slice(0, 700, 10)
        view = (y_slice, x_slice)
        data_np = aimg._slice(view)
        assert isinstance(data_np, np.ndarray)
        assert data_np.shape == (70, 99)
        assert isinstance(data_np[0, 0], np.integer)
        res = 'd6f0e61dc54f0c888c8f79d94ead85f8d3c4736efede289ff9946e0091960524'
        m = hashlib.sha256()
        m.update(str(data_np.tolist()).encode())
        assert m.hexdigest() == res

    def test_zarr_aimg_get_data_xy(self):
        """Test that we can get a single value from an AstroImage object.
        """
        aimg = AstroImage.AstroImage(logger=self.logger)
        aimg.set_data(self._getdata((5, 5), data_np=np.arange(0, 25)))

        val = int(aimg.get_data_xy(3, 3))
        assert isinstance(val, int)
        assert val == 18

    def test_zarr_fancy_scale(self):
        """Test that we can get a fancy superslice of a zarr.
        """
        arr_z = self._getdata((5, 5, 5))

        p1 = (0, 0, 0)
        p2 = (5, 5, 5)
        new_dims = (51, 51, 51)

        data_np, scales = trcalc.get_scaled_cutout_wdhtdp(arr_z, p1, p2,
                                                          new_dims,
                                                          logger=self.logger)
        assert isinstance(data_np, np.ndarray)
        assert data_np.shape == new_dims
        assert isinstance(data_np[0, 0, 0], np.integer)
        res = '4d6bb43463f435d76d226c38314fa22a5ba540b7db785b1ccfd2c75d84063fc4'
        m = hashlib.sha256()
        m.update(str(data_np.tolist()).encode())
        assert m.hexdigest() == res
