"""Test ColorDist.py"""

import numpy as np
import pytest

from ginga import ColorDist as cd


# Some of the code is based on https://github.com/ejeschke/ginga/pull/346
class TestColorDist(object):
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
        """This is to generate expected scaled output."""
        if disttype == 'histeq':
            idx = data.clip(0, self.hashsize - 1)
            hist, bins = np.histogram(
                idx.ravel(), self.hashsize, density=False)
            cdf = hist.cumsum()
            ohash = ((cdf - cdf.min()) * (self.colorlen - 1) /
                     (cdf.max() - cdf.min())).astype(int)
            idx = idx.astype(np.uint)
            result = ohash[idx]
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

            result = (out.clip(0.0, 1.0) * (self.colorlen - 1)).astype(int)

        return result

    @pytest.mark.parametrize(
        'dist_name', ['linear', 'log', 'power', 'sqrt',
                      'squared', 'asinh', 'sinh', 'histeq'])
    def test_dist_function(self, dist_name):
        dist = cd.get_dist(dist_name)(self.hashsize, colorlen=self.colorlen)
        y = dist.hash_array(self.data)
        expected_y = self.scale_and_rescale(dist_name, self.data)
        np.testing.assert_allclose(y, expected_y)
