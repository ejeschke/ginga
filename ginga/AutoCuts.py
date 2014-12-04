#
# AutoCuts.py -- class for calculating auto cut levels
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
import time
import threading

from ginga.misc import Bunch
#from ginga.misc.ParamSet import Param
from ginga.util import zscale

have_scipy = True
autocut_methods = ('minmax', 'median', 'histogram', 'stddev', 'zscale')
try:
    import scipy.ndimage.filters
    import scipy.optimize as optimize
    #import scipy.misc
except ImportError:
    have_scipy = False
    autocut_methods = ('minmax', 'histogram', 'stddev', 'zscale')

# Lock to work around a non-threadsafe bug in scipy
_lock = threading.RLock()

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
        (data, x1, y1, x2, y2) = image.cutout_radius(wd//2, ht//2,
                                                     crop_radius)
        return data
    
    def cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
        loval, hival = float(loval), float(hival)
        self.logger.debug("loval=%.2f hival=%.2f" % (loval, hival))
        delta = hival - loval
        if delta != 0.0:
            data = data.clip(loval, hival)
            f = ((data - loval) / delta)
        else:
            #f = (data - loval).clip(0.0, 1.0)
            f = data - loval
            f.clip(0.0, 1.0, out=f)
            # threshold
            f[numpy.nonzero(f)] = 1.0

        # f = f.clip(0.0, 1.0) * vmax
        # NOTE: optimization using in-place outputs for speed
        f.clip(0.0, 1.0, out=f)
        numpy.multiply(f, vmax, out=f)
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

    def cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
        return data.clip(vmin, vmax)


class Minmax(AutoCutsBase):

    def __init__(self, logger):
        super(Minmax, self).__init__(logger)
        self.kind = 'minmax'

    def calc_cut_levels(self, image):
        loval, hival = image.get_minmax()

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
        if self.usecrop:
            data = self.get_crop(image)
        else:
            data = image.get_data()
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
        dsum = numpy.sum(data)
        if numpy.isnan(dsum) or numpy.isinf(dsum):
            # Oh crap, the array has a NaN or Inf value.
            # We have to workaround this by making a copy of the array
            # and substituting for the problem values, otherwise numpy's
            # histogram() cannot handle it
            self.logger.warn("NaN's found in data, using workaround for histogram")
            data = data.copy()
            # TODO: calculate a reasonable replacement value
            data[numpy.isinf(data)] = 0.0
            minval = numpy.nanmin(data)
            maxval = numpy.nanmax(data)
            substval = (minval + maxval)/2.0
            data[numpy.isnan(data)] = substval
            data[numpy.isinf(data)] = substval
            ## dsum = numpy.sum(data)
            ## if numpy.isnan(dsum) or numpy.isinf(dsum):
            ##     print "NaNs STILL PRESENT"

            dist, bins = numpy.histogram(data, bins=numbins,
                                         density=False)
        else:
            dist, bins = numpy.histogram(data, bins=numbins,
                                         density=False)

        cutoff = int((float(total_px)*(1.0-pct))/2.0)
        top = len(dist)-1
        self.logger.debug("top=%d cutoff=%d" % (top, cutoff))
        #print "DIST: %s\nBINS: %s" % (str(dist), str(bins))

        # calculate low cutoff
        cumsum = numpy.cumsum(dist)
        li = numpy.flatnonzero(cumsum > cutoff)
        if len(li) > 0:
            i = li[0]
            count_px = cumsum[i]
        else:
            i = 0
            count_px = 0
        if i > 0:
            nprev = cumsum[i-1]
        else:
            nprev = 0
        loidx = i

        # interpolate between last two low bins
        val1, val2 = bins[i], bins[i+1]
        divisor = float(count_px) - float(nprev)
        if divisor > 0.0:
            interp = (float(cutoff)-float(nprev))/ divisor
        else:
            interp = 0.0
        loval = val1 + ((val2 - val1) * interp)
        self.logger.debug("loval=%f val1=%f val2=%f interp=%f" % (
            loval, val1, val2, interp))

        # calculate high cutoff
        revdist = dist[::-1]
        cumsum = numpy.cumsum(revdist)
        li = numpy.flatnonzero(cumsum > cutoff)
        if len(li) > 0:
            i = li[0]
            count_px = cumsum[i]
        else:
            i = 0
            count_px = 0
        if i > 0:
            nprev = cumsum[i-1]
        else:
            nprev = 0
        j = top - i
        hiidx = j+1

        # interpolate between last two high bins
        val1, val2 = bins[j], bins[j+1]
        divisor = float(count_px) - float(nprev)
        if divisor > 0.0:
            interp = (float(cutoff)-float(nprev))/ divisor
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
        if self.usecrop:
            data = self.get_crop(image)
        else:
            data = image.get_data()

        loval, hival = self.calc_stddev(data, hensa_lo=self.hensa_lo,
                                        hensa_hi=self.hensa_hi)
        return loval, hival

    def calc_stddev(self, data, hensa_lo=35.0, hensa_hi=90.0):
        # This is the method used in the old SOSS fits viewer
        mdata = numpy.ma.masked_array(data, numpy.isnan(data))
        mean = numpy.mean(mdata)
        sdev = numpy.std(mdata)
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
        wd, ht = image.get_size()
        
        # sample the data
        xmax = wd - 1
        ymax = ht - 1
        # evenly spaced sampling over rows and cols
        xskip = int(max(1.0, numpy.sqrt(xmax * ymax / float(self.num_points))))
        yskip = xskip

        cutout = image.cutout_data(0, 0, xmax, ymax,
                                   xstep=xskip, ystep=yskip)

        loval, hival = self.calc_medianfilter(cutout, length=self.length)
        return loval, hival

    def calc_medianfilter(self, data, length=5):

        assert len(data.shape) >= 2, \
               AutoCutsError("input data should be 2D or greater")
        if length is None:
            length = 5

        xout = scipy.ndimage.filters.median_filter(data, size=length)
        loval = numpy.nanmin(xout)
        hival = numpy.nanmax(xout)

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
        wd, ht = image.get_size()
        
        # calculate num_points parameter, if omitted
        total_points = wd * ht
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
        xskip = int(max(1.0, numpy.sqrt(xmax * ymax / float(num_points))))
        yskip = xskip

        cutout = image.cutout_data(0, 0, xmax, ymax,
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

        # remove NaN and Inf from samples
        samples = data[numpy.isfinite(data)].flatten()
        samples = samples[:num_points]

        loval, hival = zscale.zscale_samples(samples, contrast=contrast)
        return loval, hival


class ZScale2(AutoCutsBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='contrast', type=float,
                  default=0.25, allow_none=True,
                  description="Contrast"),
            Param(name='num_points', type=int,
                  default=600, allow_none=True,
                  description="Number of points to sample"),
            Param(name='num_per_row', type=int,
                  default=None, allow_none=True,
                  description="Number of points to sample"),
            ]

    def __init__(self, logger, contrast=0.25, num_points=1000,
                 num_per_row=None):
        super(ZScale2, self).__init__(logger)

        self.kind = 'zscale'
        self.contrast = contrast
        self.num_points = num_points
        self.num_per_row = num_per_row
        
    def calc_cut_levels(self, image):
        data = image.get_data()

        loval, hival = self.calc_zscale(data, contrast=self.contrast,
                                        num_points=self.num_points,
                                        num_per_row=self.num_per_row)
        return loval, hival

    def calc_zscale(self, data, contrast=0.25,
                    num_points=1000, num_per_row=None):
        """
        From the IRAF documentation:
        
        The zscale algorithm is designed to display the  image  values
        near the median  image value  without the  time consuming process of
        computing a full image histogram.  This is particularly  useful  for
        astronomical  images  which  generally  have a very peaked histogram
        corresponding to  the  background  sky  in  direct  imaging  or  the
        continuum in a two dimensional spectrum.

        The  sample  of pixels, specified by values greater than zero in the
        sample mask zmask or by an  image  section,  is  selected  up  to  a
        maximum  of nsample pixels.  If a bad pixel mask is specified by the
        bpmask parameter then any pixels with mask values which are  greater
        than  zero  are not counted in the sample.  Only the first pixels up
        to the limit are selected where the order is by line beginning  from
        the  first line.  If no mask is specified then a grid of pixels with
        even spacing along lines and columns that  make  up  a  number  less
        than or equal to the maximum sample size is used.

        If  a  contrast of zero is specified (or the zrange flag is used and
        the image does not have a  valid  minimum/maximum  value)  then  the
        minimum  and maximum of the sample is used for the intensity mapping
        range.

        If the contrast  is  not  zero  the  sample  pixels  are  ranked  in
        brightness  to  form  the  function I(i), where i is the rank of the
        pixel and I is its value.  Generally the midpoint of  this  function
        (the  median) is very near the peak of the image histogram and there
        is a well defined slope about the midpoint which is related  to  the
        width  of the histogram.  At the ends of the I(i) function there are
        a few very bright and dark pixels due to objects and defects in  the
        field.   To  determine  the  slope  a  linear  function  is fit with
        iterative rejection;

            I(i) = intercept + slope * (i - midpoint)

        If more than half of the points are rejected then there is  no  well
        defined  slope  and  the full range of the sample defines z1 and z2.
        Otherwise the endpoints of the linear function  are  used  (provided
        they are within the original range of the sample):

            z1 = I(midpoint) + (slope / contrast) * (1 - midpoint)
            z2 = I(midpoint) + (slope / contrast) * (npoints - midpoint)

        As  can  be  seen,  the parameter contrast may be used to adjust the
        contrast produced by this algorithm.
        """

        assert len(data.shape) >= 2, \
               AutoCutsError("input data should be 2D or greater")
        ht, wd = data.shape[:2]

        assert (0.0 < contrast <= 1.0), \
               AutoCutsError("contrast (%.2f) not in range 0 < c <= 1" % (
            contrast))

        # calculate num_points parameter, if omitted
        total_points = numpy.size(data)
        if num_points is None:
            num_points = max(int(total_points * 0.0002), 600)
        num_points = min(num_points, total_points)

        assert (0 < num_points <= total_points), \
               AutoCutsError("num_points not in range 0-%d" % (total_points))

        # calculate num_per_row parameter, if omitted
        if num_per_row is None:
            num_per_row = max(int(0.015 * num_points), 1)
        self.logger.debug("contrast=%.4f num_points=%d num_per_row=%d" % (
            contrast, num_points, num_per_row))

        # sample the data
        num_rows = num_points // num_per_row
        xmax = wd - 1
        xskip = max(xmax // num_per_row, 1)
        ymax = ht - 1
        yskip = max(ymax // num_rows, 1)
        # evenly spaced sampling over rows and cols
        ## xskip = int(max(1.0, numpy.sqrt(xmax * ymax / float(num_points))))
        ## yskip = xskip

        cutout = data[0:ymax:yskip, 0:xmax:xskip]
        # flatten and trim off excess
        cutout = cutout.flat[0:num_points]

        # actual number of points selected
        num_pix = len(cutout)
        assert num_pix <= num_points, \
               AutoCutsError("Actual number of points (%d) exceeds calculated number (%d)" % (
            num_pix, num_points))

        # sort the data by value
        cutout = numpy.sort(cutout)

        # flat distribution?
        data_min = numpy.nanmin(cutout)
        data_max = numpy.nanmax(cutout)
        if (data_min == data_max) or (contrast == 0.0):
            return (data_min, data_max)

        # compute the midpoint and median
        midpoint = (num_pix // 2)
        if num_pix % 2 != 0:
            median = cutout[midpoint]
        else:
            median = 0.5 * (cutout[midpoint-1] + cutout[midpoint])
        self.logger.debug("num_pix=%d midpoint=%d median=%.4f" % (
            num_pix, midpoint, median))

        ## # Remove outliers to aid fitting
        ## threshold = numpy.std(cutout) * 2.5
        ## cutout = cutout[numpy.where(numpy.fabs(cutout - median) > threshold)]
        ## num_pix = len(cutout)
        
        # zscale fitting function:
        # I(x) = slope * (x - midpoint) + intercept
        def fitting(x, slope, intercept):
            y = slope * (x - midpoint) + intercept
            return y

        # compute a least squares fit 
        X = numpy.arange(num_pix)
        Y = cutout
        sigma = numpy.array([ 1.0 ]* num_pix)
        guess = numpy.array([0.0, 0.0])

        # Curve fit
        with _lock:
            # NOTE: without this mutex, optimize.curvefit causes a fatal error
            # sometimes--it appears not to be thread safe.
            # The error is:
            # "SystemError: null argument to internal routine"
            # "Fatal Python error: GC object already tracked"
            try:
                p, cov = optimize.curve_fit(fitting, X, Y, guess, sigma)

            except Exception as e:
                self.logger.debug("curve fitting failed: %s" % (str(e)))
                cov = None
            
        if cov is None:
            self.logger.debug("curve fitting failed")
            return (float(data_min), float(data_max))

        slope, intercept = p
        num_chosen = 0
        self.logger.debug("intercept=%f slope=%f" % (
            intercept, slope))

        ## if num_chosen < (num_pix // 2):
        ##     self.logger.debug("more than half pixels rejected--falling back to min/max of sample")
        ##     return (data_min, data_max)

        # finally, compute the range
        falloff = slope / contrast
        z1 = median - midpoint * falloff
        z2 = median + (num_pix - midpoint) * falloff

        # final sanity check on cut levels
        locut = max(z1, data_min)
        hicut = min(z2, data_max)
        if locut >= hicut:
            locut = data_min
            hicut = data_max

        return (float(locut), float(hicut))

# funky boolean converter
_bool = lambda st: str(st).lower() == 'true'


autocuts_table = {
    'clip': Clip,
    'minmax': Minmax,
    'stddev': StdDev,
    'histogram': Histogram,
    'median': MedianFilter,
    'zscale': ZScale,
    'zscale2': ZScale2,
    }

def get_autocuts(name):
    if not name in autocut_methods:
        raise AutoCutsError("Method '%s' is not supported" % (name))

    return autocuts_table[name]


# END
