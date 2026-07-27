"""Test ColorDist.py"""

import warnings

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


class TestColorDistBackwardCompat:
    """Regression tests for the pre-7.1 ColorDist compatibility shim
    (github issue #1148): older subclasses filled ``hash`` with integer
    indices scaled by ``colorlen`` instead of a normalized 0.0-1.0 curve.
    """
    hashsize = 256
    colorlen = 256

    def _old_int_dist_cls(self):
        class OldIntDist(cd.ColorDistBase):
            # pre-7.1 contract: fill `hash` with integer indices scaled by
            # colorlen-1, set directly (no set_hash), like a linear ramp
            def calc_hash(self):
                x = np.arange(self.hashsize) / self.hashsize
                self.hash = (x * (self.colorlen - 1)).astype(int)

            def get_dist_pct(self, pct):
                return np.clip(np.asarray(pct, dtype=float), 0.0, 1.0)
        return OldIntDist

    def test_old_integer_hash_normalized_with_warning(self):
        cls = self._old_int_dist_cls()
        with pytest.warns(PendingDeprecationWarning):
            dist = cls(self.hashsize, colorlen=self.colorlen)
        assert dist.hash.dtype == np.float32
        assert dist.hash.min() >= 0.0 and dist.hash.max() <= 1.0
        # migrated curve matches a linear 0..1 ramp
        linear = cd.LinearDist(self.hashsize).hash
        np.testing.assert_allclose(dist.hash, linear,
                                   atol=1.0 / (self.colorlen - 1))
        # hash_array now returns the normalized curve
        y = dist.hash_array(np.arange(self.hashsize, dtype=int))
        assert y.min() >= 0.0 and y.max() <= 1.0

    def test_old_float_scaled_hash_normalized_with_warning(self):
        class OldFloatDist(cd.ColorDistBase):
            def calc_hash(self):
                x = np.arange(self.hashsize) / self.hashsize
                self.hash = x * (self.colorlen - 1)   # float, max ~255

            def get_dist_pct(self, pct):
                return np.clip(np.asarray(pct, dtype=float), 0.0, 1.0)
        with pytest.warns(PendingDeprecationWarning):
            dist = OldFloatDist(self.hashsize, colorlen=self.colorlen)
        assert dist.hash.dtype == np.float32
        assert dist.hash.max() <= 1.0

    def test_old_dist_through_distribute_no_garbage(self):
        # the reported bug: old integer hash was double-scaled to garbage
        # indices (e.g. max 64770 instead of 255) with no error
        from ginga.util.stages.color import Distribute
        cls = self._old_int_dist_cls()
        data = np.arange(self.hashsize, dtype=np.uint32)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PendingDeprecationWarning)
            dist = cls(self.hashsize, colorlen=self.colorlen)
            stage = Distribute(bpp=8)
            stage.set_dist(dist)
            out = stage.get_hasharray(data)
        assert out.dtype == np.uint8
        assert out.max() <= 255            # not garbage (was ~64770)
        # a near-linear ramp: matches the built-in linear distribution to
        # within one level (the old integer hash truncated, losing <1 level)
        lin = Distribute(bpp=8)
        lin.set_color_algorithm('linear')
        diff = np.abs(out.astype(int) - lin.get_hasharray(data).astype(int))
        assert diff.max() <= 1
        assert np.all(np.diff(out.astype(int)) >= 0)   # monotonic ramp

    def test_set_hash_size_remigrates_old_dist(self):
        cls = self._old_int_dist_cls()
        with pytest.warns(PendingDeprecationWarning):
            dist = cls(self.hashsize, colorlen=self.colorlen)
        with pytest.warns(PendingDeprecationWarning):
            dist.set_hash_size(512)
        assert len(dist.hash) == 512
        assert dist.hash.dtype == np.float32 and dist.hash.max() <= 1.0

    def test_new_style_subclass_does_not_warn(self):
        class NewDist(cd.ColorDistBase):
            def calc_hash(self):
                x = np.arange(self.hashsize) / self.hashsize
                self.set_hash(x)           # normalized 0..1 via public API

            def get_dist_pct(self, pct):
                return np.clip(np.asarray(pct, dtype=float), 0.0, 1.0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", PendingDeprecationWarning)
            dist = NewDist(self.hashsize)
        assert dist.hash.dtype == np.float32 and dist.hash.max() <= 1.0

    def test_builtin_dists_do_not_warn(self):
        # no false positives for the shipped distributions
        with warnings.catch_warnings():
            warnings.simplefilter("error", PendingDeprecationWarning)
            for name in cd.get_dist_names():
                cd.get_dist(name)(self.hashsize)

    def test_set_hash_public_and_alias(self):
        # public set_hash() and the deprecated _set_hash alias are the same
        assert cd.ColorDistBase._set_hash is cd.ColorDistBase.set_hash
        dist = cd.LinearDist(self.hashsize)
        dist.set_hash(np.linspace(0.0, 1.0, self.hashsize))
        assert dist.hash.dtype == np.float32 and dist.hash.max() <= 1.0
        dist._set_hash(np.linspace(0.0, 1.0, self.hashsize))
        assert dist.hash.max() <= 1.0
