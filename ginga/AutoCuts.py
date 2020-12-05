#
# AutoCuts.py -- class for calculating auto cut levels
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc
from ginga.misc import Bunch
#from ginga.misc.ParamSet import Param
from ginga.util import zscale

have_scipy = True
autocut_methods = ('minmax', 'median', 'histogram', 'stddev', 'zscale')
try:
    import scipy.ndimage.filters
except ImportError:
    have_scipy = False
    autocut_methods = ('minmax', 'histogram', 'stddev', 'zscale')


class Param(Bunch.Bunch):
    pass


class AutoCutsError(Exception):
    pass


class AutoCutsBase(object):

    @classmethod
    def get_params_metadata(cls):
        return []

    def __init__(self, logger):
        super(AutoCutsBase, self).__init__()

        self.logger = logger
        self.kind = 'base'
        self.crop_radius = 512

    def update_params(self, **param_dict):
        # TODO: find a cleaner way to update these
        self.__dict__.update(param_dict)

    def get_algorithms(self):
        return autocut_methods

    def get_autocut_levels(self, image):
        loval, hival = self.calc_cut_levels(image)
        return loval, hival

    def get_crop(self, image, crop_radius=None):
        # Even with numpy, it's kind of slow for some of the autocut
        # methods on a large image, so in those cases we can optionally
        # take a crop of size (radius*2)x(radius*2) from the center of
        # the image and calculate the cut levels on that
        if crop_radius is None:
            crop_radius = self.crop_radius

        wd, ht = image.get_size()
        (data, x1, y1, x2, y2) = image.cutout_radius(wd // 2, ht // 2,
                                                     crop_radius)
        return data

    def get_crop_data(self, data, crop_radius=None):
        if crop_radius is None:
            crop_radius = self.crop_radius

        ht, wd = data.shape[:2]
        (data, x1, y1, x2, y2) = trcalc.cutout_radius(data, wd // 2, ht // 2,
                                                      crop_radius)
        return data

    def cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
        loval, hival = float(loval), float(hival)
        # ensure hival >= loval
        hival = max(loval, hival)
        self.logger.debug("loval=%.2f hival=%.2f" % (loval, hival))
        delta = hival - loval
        if delta > 0.0:
            f = (((data - loval) / delta) * vmax)
            # NOTE: optimization using in-place outputs for speed
            f.clip(0.0, vmax, out=f)
            return f

        # hival == loval, so thresholding operation
        f = (data - loval).clip(0.0, vmax)
        f[f > 0.0] = vmax
        return f

    def __str__(self):
        return self.kind


class Clip(AutoCutsBase):

    def __init__(self, logger):
        super(Clip, self).__init__(logger)
        self.kind = 'clip'

    def calc_cut_levels(self, image):
        loval, hival = image.get_minmax()

        return (float(loval), float(hival))

    def calc_cut_levels_data(self, data_np):
        loval = np.nanmin(data_np)
        hival = np.nanmax(data_np)

        return (float(loval), float(hival))

    def cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
        return data.clip(vmin, vmax)


class Minmax(AutoCutsBase):

    def __init__(self, logger):
        super(Minmax, self).__init__(logger)
        self.kind = 'minmax'

    def calc_cut_levels(self, image):
        loval, hival = image.get_minmax()

        return (float(loval), float(hival))

    def calc_cut_levels_data(self, data_np):
        loval = np.nanmin(data_np)
        hival = np.nanmax(data_np)

        return (float(loval), float(hival))


class Histogram(AutoCutsBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='usecrop', type=_bool,
                  valid=[True, False],
                  default=True,
                  description="Use center crop of image for speed"),
            Param(name='pct', type=float,
                  widget='spinfloat', incr=0.001,
                  min=0.0, max=1.0, default=0.999,
                  description="Percentage of the histogram to retain"),
            Param(name='numbins', type=int,
                  min=100, max=10000, default=2048,
                  description="Number of bins for the histogram"),
        ]

    def __init__(self, logger, usecrop=True, pct=0.999, numbins=2048):
        super(Histogram, self).__init__(logger)

        self.kind = 'histogram'
        self.usecrop = usecrop
        self.pct = pct
        self.numbins = numbins

    def calc_cut_levels(self, image):
        data = image.get_data()
        return self.calc_cut_levels_data(data)

    def calc_cut_levels_data(self, data_np):
        if self.usecrop:
            data = self.get_crop_data(data_np)
            count = np.count_nonzero(np.isfinite(data))
            if count < (self.crop_radius ** 2.0) * 0.50:
                # if we have less than 50% finite pixels then fall back
                # to using the whole array
                self.logger.debug("too many non-finite values in crop--"
                                  "falling back to full image data")
                data = data_np
        else:
            data = data_np

        bnch = self.calc_histogram(data, pct=self.pct, numbins=self.numbins)
        loval, hival = bnch.loval, bnch.hival
        return loval, hival

    def calc_histogram(self, data, pct=1.0, numbins=2048):

        self.logger.debug("Computing histogram, pct=%.4f numbins=%d" % (
            pct, numbins))
        height, width = data.shape[:2]
        self.logger.debug("Median analysis array is %dx%d" % (
            width, height))

        total_px = width * height
        dsum = np.sum(data)
        if np.isnan(dsum) or np.isinf(dsum):
            # Oh crap, the array has a NaN or Inf value.
            # We have to workaround this by making a copy of the array
            # and substituting for the problem values, otherwise numpy's
            # histogram() cannot handle it
            self.logger.warning("NaN's found in data, using workaround for histogram")
            data = data.copy()
            # TODO: calculate a reasonable replacement value
            data[np.isinf(data)] = 0.0
            minval = np.nanmin(data)
            maxval = np.nanmax(data)
            substval = (minval + maxval) / 2.0
            data[np.isnan(data)] = substval
            data[np.isinf(data)] = substval

            dist, bins = np.histogram(data, bins=numbins,
                                      density=False)
        else:
            dist, bins = np.histogram(data, bins=numbins,
                                      density=False)

        cutoff = int((float(total_px) * (1.0 - pct)) / 2.0)
        top = len(dist) - 1
        self.logger.debug("top=%d cutoff=%d" % (top, cutoff))

        # calculate low cutoff
        cumsum = np.cumsum(dist)
        li = np.flatnonzero(cumsum > cutoff)
        if len(li) > 0:
            i = li[0]
            count_px = cumsum[i]
        else:
            i = 0
            count_px = 0
        if i > 0:
            nprev = cumsum[i - 1]
        else:
            nprev = 0
        loidx = i

        # interpolate between last two low bins
        val1, val2 = bins[i], bins[i + 1]
        divisor = float(count_px) - float(nprev)
        if divisor > 0.0:
            interp = (float(cutoff) - float(nprev)) / divisor
        else:
            interp = 0.0
        loval = val1 + ((val2 - val1) * interp)
        self.logger.debug("loval=%f val1=%f val2=%f interp=%f" % (
            loval, val1, val2, interp))

        # calculate high cutoff
        revdist = dist[::-1]
        cumsum = np.cumsum(revdist)
        li = np.flatnonzero(cumsum > cutoff)
        if len(li) > 0:
            i = li[0]
            count_px = cumsum[i]
        else:
            i = 0
            count_px = 0
        if i > 0:
            nprev = cumsum[i - 1]
        else:
            nprev = 0
        j = top - i
        hiidx = j + 1

        # interpolate between last two high bins
        val1, val2 = bins[j], bins[j + 1]
        divisor = float(count_px) - float(nprev)
        if divisor > 0.0:
            interp = (float(cutoff) - float(nprev)) / divisor
        else:
            interp = 0.0
        hival = val1 + ((val2 - val1) * interp)
        self.logger.debug("hival=%f val1=%f val2=%f interp=%f" % (
            hival, val1, val2, interp))

        return Bunch.Bunch(dist=dist, bins=bins, loval=loval, hival=hival,
                           loidx=loidx, hiidx=hiidx)


class StdDev(AutoCutsBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='usecrop', type=_bool,
                  valid=[True, False],
                  default=True,
                  description="Use center crop of image for speed"),
            ## Param(name='hensa_lo', type=float, default=35.0,
            ##             description="Low subtraction factor"),
            ## Param(name='hensa_hi', type=float, default=90.0,
            ##             description="High subtraction factor"),
        ]

    def __init__(self, logger, usecrop=True):
        super(StdDev, self).__init__(logger)

        self.kind = 'stddev'
        # Constants used to calculate the lo and hi cut levels using the
        # "stddev" algorithm (from the old SOSS fits viewer)
        self.usecrop = usecrop
        self.hensa_lo = 35.0
        self.hensa_hi = 90.0

    def calc_cut_levels(self, image):
        data = image.get_data()
        return self.calc_cut_levels_data(data)

    def calc_cut_levels_data(self, data_np):
        if self.usecrop:
            data = self.get_crop_data(data_np)
            count = np.count_nonzero(np.isfinite(data))
            if count < (self.crop_radius ** 2.0) * 0.50:
                # if we have less than 50% finite pixels then fall back
                # to using the whole array
                self.logger.info("too many non-finite values in crop--"
                                 "falling back to full image data")
                data = data_np
        else:
            data = data_np

        loval, hival = self.calc_stddev(data_np, hensa_lo=self.hensa_lo,
                                        hensa_hi=self.hensa_hi)
        return loval, hival

    def calc_stddev(self, data, hensa_lo=35.0, hensa_hi=90.0):
        # This is the method used in the old SOSS fits viewer
        mdata = np.ma.masked_array(data, np.isnan(data))
        mean = np.mean(mdata)
        sdev = np.std(mdata)
        self.logger.debug("mean=%f std=%f" % (mean, sdev))

        hensa_lo_factor = (hensa_lo - 50.0) / 10.0
        hensa_hi_factor = (hensa_hi - 50.0) / 10.0

        loval = hensa_lo_factor * sdev + mean
        hival = hensa_hi_factor * sdev + mean

        return loval, hival


class MedianFilter(AutoCutsBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='usecrop', type=_bool,
            ##             valid=set([True, False]),
            ##             default=True,
            ##             description="Use center crop of image for speed"),
            Param(name='num_points', type=int,
                  default=2000, allow_none=True,
                  description="Number of points to sample"),
            Param(name='length', type=int, default=5,
                  description="Median kernel length"),
        ]

    def __init__(self, logger, num_points=2000, length=5):
        super(MedianFilter, self).__init__(logger)

        self.kind = 'median'
        self.num_points = num_points
        self.length = length

    def calc_cut_levels(self, image):
        data = image.get_data()
        return self.calc_cut_levels_data(data)

    def calc_cut_levels_data(self, data_np):
        ht, wd = data_np.shape[:2]

        # sample the data
        xmax = wd - 1
        ymax = ht - 1
        # evenly spaced sampling over rows and cols
        xskip = int(max(1.0, np.sqrt(xmax * ymax / float(self.num_points))))
        yskip = xskip

        cutout = trcalc.cutout_data(data_np, 0, 0, xmax, ymax,
                                    xstep=xskip, ystep=yskip)

        loval, hival = self.calc_medianfilter(cutout, length=self.length)
        return loval, hival

    def calc_medianfilter(self, data, length=5):

        assert len(data.shape) >= 2, \
            AutoCutsError("input data should be 2D or greater")
        if length is None:
            length = 5

        xout = scipy.ndimage.filters.median_filter(data, size=length)
        loval = np.nanmin(xout)
        hival = np.nanmax(xout)

        return loval, hival


class ZScale(AutoCutsBase):
    """
    Based on STScI's numdisplay implementation of IRAF's ZScale.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='contrast', type=float,
                  default=0.25, allow_none=False,
                  description="Contrast"),
            Param(name='num_points', type=int,
                  default=1000, allow_none=True,
                  description="Number of points to sample"),
        ]

    def __init__(self, logger, contrast=0.25, num_points=1000):
        super(ZScale, self).__init__(logger)

        self.kind = 'zscale'
        self.contrast = contrast
        self.num_points = num_points

    def calc_cut_levels(self, image):
        data = image.get_data()
        return self.calc_cut_levels_data(data)

    def calc_cut_levels_data(self, data_np):
        ht, wd = data_np.shape[:2]

        # calculate num_points parameter, if omitted
        total_points = wd * ht
        if total_points == 0:
            self.logger.debug('total_points is 0, setting cut levels to 0')
            return 0, 0
        num_points = self.num_points
        if num_points is None:
            num_points = max(int(total_points * 0.0002), 1000)
        num_points = min(num_points, total_points)

        assert (0 < num_points <= total_points), \
            AutoCutsError("num_points not in range 0-%d" % (total_points))

        # sample the data
        xmax = wd - 1
        ymax = ht - 1
        # evenly spaced sampling over rows and cols
        xskip = int(max(1.0, np.sqrt(xmax * ymax / float(num_points))))
        yskip = xskip

        cutout = trcalc.cutout_data(data_np, 0, 0, xmax, ymax,
                                    xstep=xskip, ystep=yskip)

        loval, hival = self.calc_zscale(cutout, contrast=self.contrast,
                                        num_points=self.num_points)
        return loval, hival

    def calc_zscale(self, data, contrast=0.25, num_points=1000):
        # NOTE: num_per_row is ignored in this implementation

        assert len(data.shape) >= 2, \
            AutoCutsError("input data should be 2D or greater")
        ht, wd = data.shape[:2]

        # sanity check on contrast parameter
        assert (0.0 < contrast <= 1.0), \
            AutoCutsError("contrast (%.2f) not in range 0 < c <= 1" % (
                contrast))

        # remove masked elements, they cause problems
        data = data[np.logical_not(np.ma.getmaskarray(data))]
        # remove NaN and Inf from samples
        samples = data[np.isfinite(data)].flatten()
        samples = samples[:num_points]

        loval, hival = zscale.zscale_samples(samples, contrast=contrast)
        return loval, hival


# funky boolean converter
_bool = lambda st: str(st).lower() == 'true'  # noqa

autocuts_table = {
    'clip': Clip,
    'minmax': Minmax,
    'stddev': StdDev,
    'histogram': Histogram,
    'median': MedianFilter,
    'zscale': ZScale,
}


def get_autocuts(name):
    if name not in autocut_methods:
        raise AutoCutsError("Method '%s' is not supported" % (name))

    return autocuts_table[name]


def get_autocuts_names():
    l = list(autocuts_table.keys())
    l.sort()
    return l

# END
