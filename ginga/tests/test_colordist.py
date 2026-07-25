"""Test ColorDist.py"""

import numpy as np
import pytest

from ginga import ColorDist as cd


# Some of the code is based on https://github.com/ejeschke/ginga/pull/346
class TestColorDist:
    def setup_class(self):
        self.hashsize = 256
        self.colorlen = 256

        # Factors used in some of the distributions
        self.a = 1000
        self.factor = 10.0
        self.nonlinearity = 3.0

        # Input data
        self.data = np.arange(self.hashsize, dtype=int)

    def scale_and_rescale(self, disttype, data):
        """Generate the expected normalized (0.0-1.0) distribution curve.

        The ColorDist classes now return the curve in 0.0-1.0 (the scaling
        to an output level happens downstream in the Distribute stage).
        """
        if disttype == 'histeq':
            idx = data.clip(0, self.hashsize - 1)
            hist, bins = np.histogram(
                idx.ravel(), self.hashsize, density=False)
            cdf = hist.cumsum()
            base = (cdf - cdf.min()) / (cdf.max() - cdf.min())
            result = base[idx]
        else:
            x = data / self.hashsize

            if disttype == 'linear':
                out = x
            elif disttype == 'log':
                out = np.log(self.a * x + 1) / np.log(self.a)
            elif disttype == 'power':
                out = (np.power(self.a, x) - 1.0) / self.a
            elif disttype == 'sqrt':
                out = np.sqrt(x)
            elif disttype == 'squared':
                out = x * x
            elif disttype == 'asinh':
                out = np.arcsinh(self.factor * x) / self.nonlinearity
            elif disttype == 'sinh':
                out = np.sinh(self.nonlinearity * x) / self.factor

            result = out.clip(0.0, 1.0)

        return result

    @pytest.mark.parametrize(
        'dist_name', ['linear', 'log', 'power', 'sqrt',
                      'squared', 'asinh', 'sinh', 'histeq'])
    def test_dist_function(self, dist_name):
        # hash_array now returns the normalized 0.0-1.0 curve (float32)
        dist = cd.get_dist(dist_name)(self.hashsize, colorlen=self.colorlen)
        y = dist.hash_array(self.data)
        assert y.dtype == np.float32
        assert y.min() >= 0.0 and y.max() <= 1.0
        expected_y = self.scale_and_rescale(dist_name, self.data)
        np.testing.assert_allclose(y, expected_y, rtol=0, atol=1e-6)

    @pytest.mark.parametrize(
        'dist_name', ['linear', 'log', 'power', 'sqrt',
                      'squared', 'asinh', 'sinh'])
    def test_distribute_scales_to_output_level(self, dist_name):
        # the Distribute stage scales the 0.0-1.0 curve to the output level
        # (bit depth) and quantizes to the minimal-width integer index
        from ginga.util.stages.color import Distribute

        # bpp=8: the stage's dist hashsize is maxc+1 == 256 == self.hashsize,
        # so we can compare exact values against the reference curve
        stage = Distribute(bpp=8)
        stage.set_color_algorithm(dist_name)
        out = stage.get_hasharray(self.data.astype(np.uint32))
        assert out.dtype == np.uint8
        curve = self.scale_and_rescale(dist_name, self.data)
        expected = np.round(curve * 255).astype(np.uint8)
        np.testing.assert_array_equal(out, expected)

        # bpp=16: output is the wider index dtype spanning 0..maxc
        stage16 = Distribute(bpp=16)
        stage16.set_color_algorithm(dist_name)
        out16 = stage16.get_hasharray(self.data.astype(np.uint32))
        assert out16.dtype == np.uint16
        assert out16.min() >= 0 and out16.max() <= 65535
