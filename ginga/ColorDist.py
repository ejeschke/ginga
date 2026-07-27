#
# ColorDist.py -- Color Distribution algorithms
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
These algorithms are modeled after the ones described for ds9 here:

    http://ds9.si.edu/doc/ref/how.html

"""
import warnings

import numpy as np


class ColorDistError(Exception):
    pass


class ColorDistBase:

    def __init__(self, hashsize, colorlen=None):
        super(ColorDistBase, self).__init__()

        self.hashsize = hashsize
        # NOTE: `colorlen` is vestigial and DEPRECATED.  The distribution
        # now produces a normalized 0.0-1.0 floating point curve; the output
        # level (bit depth) is applied downstream by the Distribute stage
        # (see ginga.util.stages.color.Distribute).  The kwarg is still
        # accepted for backward compatibility but has no effect.
        self.colorlen = 256 if colorlen is None else colorlen
        self.maxhashsize = 1024 * 1024
        # holds the hash array: a float32 lookup table of `hashsize` values,
        # each in 0.0-1.0
        self.hash = None
        self.calc_hash()
        # validate/normalize the hash produced by calc_hash (skipped when a
        # subclass -- e.g. histeq -- defers building it to hash_array())
        if self.hash is not None:
            self.check_hash()

    def set_hash(self, base):
        """Install the normalized (0.0-1.0) distribution curve `base` as the
        hash LUT.  Subclasses should call this from ``calc_hash()``.
        """
        self.hash = np.clip(base, 0.0, 1.0).astype(np.float32, copy=False)
        self._check_length()

    # deprecated internal name kept for backward compatibility
    _set_hash = set_hash

    def hash_array(self, idx):
        # `idx` are integer indices assumed to be in 0..hashsize-1;
        # clip as a precaution.  Returns float32 values in 0.0-1.0.
        idx = np.clip(idx, 0, self.hashsize - 1)
        return self.hash[idx]

    def get_hash_size(self):
        return self.hashsize

    def set_hash_size(self, size):
        assert (size >= self.colorlen) and (size <= self.maxhashsize), \
            ColorDistError("Bad hash size!")
        self.hashsize = size
        self.calc_hash()
        if self.hash is not None:
            self.check_hash()

    def _check_length(self):
        hashlen = len(self.hash)
        assert hashlen == self.hashsize, \
            ColorDistError("Computed hash table size (%d) != specified size "
                           "(%d)" % (hashlen, self.hashsize))

    def check_hash(self):
        """Validate the hash LUT.

        Checks the table length and -- for backward compatibility -- detects
        and normalizes a pre-7.1 hash.  Older ``ColorDist`` subclasses filled
        ``hash`` with integer indices scaled by ``colorlen`` instead of a
        normalized 0.0-1.0 float curve; feeding those to the (now
        output-scaling) ``Distribute`` stage produced silent garbage.  We
        detect that here and normalize, emitting a
        ``PendingDeprecationWarning`` (a soft, pre-deprecation signal for
        this grace-period release).

        This runs once per hash build (from ``__init__`` / ``set_hash_size``),
        never per pixel, so it has no per-frame cost.  The compatibility
        shim will be removed in a future release.
        """
        self._check_length()
        hsh = self.hash
        # An integer dtype, or float values well above the 0.0-1.0 range
        # (old curves scale up to ``colorlen - 1``), indicate the old
        # contract.  The 1.5 threshold sits safely between the new
        # contract's 1.0 ceiling and the old contract's ~colorlen floor, so
        # float round-off can't trigger a false positive.
        if (not np.issubdtype(hsh.dtype, np.floating) or
                (hsh.size > 0 and np.nanmax(hsh) > 1.5)):
            warnings.warn(
                "ColorDist.calc_hash() produced a non-normalized hash "
                "(integer or > 1.0 values); normalizing to 0.0-1.0 for "
                "backward compatibility.  Update calc_hash() to install a "
                "normalized float curve via set_hash().  This compatibility "
                "shim will be removed in a future release.",
                PendingDeprecationWarning, stacklevel=2)
            denom = max(self.colorlen - 1, 1)
            self.hash = np.clip(np.asarray(hsh, dtype=np.float32) / denom,
                                0.0, 1.0)

    def calc_hash(self):
        """Create the hash table that implements the distribution function.
        """
        raise ColorDistError("Subclass needs to override this method")

    def get_dist_pct(self, pct):
        """Calculate a domain value based on a percentage into the range.

        Given a value between 0 and 1, calculate the value in the domain
        that corresponds to this percentage of the distribution range.
        This function is primarily used to build color bars for display.

        Parameters
        ----------
        pct : float
            A floating point value between 0 and 1

        Returns
        -------
        val : float
            A value in the domain of the color distribution function
        """
        raise ColorDistError("Subclass needs to override this method")


class LinearDist(ColorDistBase):
    """
    y = x
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None):
        super(LinearDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        val = np.clip(pct, 0.0, 1.0)
        return val

    def __str__(self):
        return 'linear'


class LogDist(ColorDistBase):
    """
    y = log(a*x + 1) / log(a)
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None, exp=1000.0):
        self.exp = exp
        super(LogDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = np.log(self.exp * base + 1.0) / np.log(self.exp)
        base = base.clip(0.0, 1.0)
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        val_inv = (np.exp(pct * np.log(self.exp)) - 1) / self.exp
        val = np.clip(val_inv, 0.0, 1.0)
        return val

    def __str__(self):
        return 'log'


class PowerDist(ColorDistBase):
    """
    y = ((a ** x) - 1) / a
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None, exp=1000.0):
        self.exp = exp
        super(PowerDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = (self.exp ** base - 1.0) / self.exp
        base = base.clip(0.0, 1.0)
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        val_inv = np.log(self.exp * pct + 1) / np.log(self.exp)
        val = np.clip(val_inv, 0.0, 1.0)
        return val

    def __str__(self):
        return 'power'


class SqrtDist(ColorDistBase):
    """
    y = sqrt(x)
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None):
        super(SqrtDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = np.sqrt(base)
        base = base.clip(0.0, 1.0)
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        val_inv = pct ** 2.0
        val = np.clip(val_inv, 0.0, 1.0)
        return val

    def __str__(self):
        return 'sqrt'


class SquaredDist(ColorDistBase):
    """
    y = x ** 2
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None):
        super(SquaredDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = (base ** 2.0)
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        val_inv = np.sqrt(pct)
        val = np.clip(val_inv, 0.0, 1.0)
        return val

    def __str__(self):
        return 'squared'


class AsinhDist(ColorDistBase):
    """
    y = asinh(nonlinearity * x) / factor
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None, factor=10.0,
                 nonlinearity=3.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(AsinhDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = np.arcsinh(self.factor * base) / self.nonlinearity
        base = base.clip(0.0, 1.0)
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        # calculate inverse of dist fn
        val_inv = np.sinh(self.nonlinearity * pct) / self.factor
        val = np.clip(val_inv, 0.0, 1.0)
        return val

    def __str__(self):
        return 'asinh'


class SinhDist(ColorDistBase):
    """
    y = sinh(factor * x) / nonlinearity
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None, factor=3.0,
                 nonlinearity=10.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(SinhDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = np.sinh(self.factor * base) / self.nonlinearity
        base = base.clip(0.0, 1.0)
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        # calculate inverse of dist fn
        val_inv = np.arcsinh(self.nonlinearity * pct) / self.factor
        val = np.clip(val_inv, 0.0, 1.0)
        return val

    def __str__(self):
        return 'sinh'


class HistogramEqualizationDist(ColorDistBase):
    """
    The histogram equalization distribution function distributes colors
    based on the frequency of each data value.
    """

    def __init__(self, hashsize, colorlen=None):
        super(HistogramEqualizationDist, self).__init__(hashsize,
                                                        colorlen=colorlen)

    def calc_hash(self):
        pass

    # TODO: this method has a lot more overhead compared to the other
    # scaling methods because the hash array must be computed each time
    # the data is delivered to hash_array()--in the other scaling
    # methods it is precomputed in calc_hash().  Investigate whether
    # there is a way to make this more efficient.
    #
    def hash_array(self, idx):
        # NOTE: data could be assumed to be in the range 0..hashsize-1
        # at this point but clip as a precaution
        idx = np.clip(idx, 0, self.hashsize - 1)

        # get image histogram
        hist, bins = np.histogram(idx.ravel(), self.hashsize, density=False)
        cdf = hist.cumsum()

        # normalize the CDF to the 0.0-1.0 curve (scaling to the output
        # level happens downstream in the Distribute stage)
        lo, hi = cdf.min(), cdf.max()
        if hi > lo:
            base = (cdf - lo) / (hi - lo)
        else:
            # flat image: avoid a divide-by-zero
            base = np.zeros(self.hashsize, dtype=np.float32)
        self.set_hash(base)

        return self.hash[idx]

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        # TODO: this is wrong but we need a way to invert the hash
        val = np.clip(pct, 0.0, 1.0)
        return pct

    def __str__(self):
        return 'histeq'


class CurveDist(ColorDistBase):
    """
    y = x
        where x in (0..1)
    """

    def __init__(self, hashsize, colorlen=None):
        super(CurveDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = np.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        self.set_hash(base)

    def get_dist_pct(self, pct):
        pct = np.asarray(pct, dtype=float)
        val = np.clip(pct, 0.0, 1.0)
        return val

    def __str__(self):
        return 'curve'


distributions = {
    'linear': LinearDist,
    'log': LogDist,
    'power': PowerDist,
    'sqrt': SqrtDist,
    'squared': SquaredDist,
    'asinh': AsinhDist,
    'sinh': SinhDist,
    'histeq': HistogramEqualizationDist,
}


def add_dist(name, distClass):
    global distributions
    distributions[name.lower()] = distClass


def get_dist_names():
    a_names = set(distributions.keys())
    std_names = ['linear', 'log', 'power', 'sqrt', 'squared', 'asinh', 'sinh',
                 'histeq']
    rest = a_names - set(std_names)
    if len(rest) > 0:
        std_names = std_names + list(rest)
    return std_names


def get_dist(name):
    if name not in distributions:
        raise ColorDistError("Invalid distribution algorithm '%s'" % (name))
    return distributions[name]

# END
