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

have_scipy = True
# TODO: remove median until we figure out why it is so slow
#autocut_methods = ('minmax', 'median', 'histogram', 'stddev', 'zscale')
autocut_methods = ('minmax', 'histogram', 'stddev', 'zscale')
try:
    import scipy.ndimage.filters
    import scipy.optimize as optimize
    #import scipy.misc
except ImportError:
    have_scipy = False
    autocut_methods = ('minmax', 'histogram', 'stddev')

# Lock to work around a non-threadsafe bug in scipy
_lock = threading.RLock()

class AutoCutsError(Exception):
    pass

class AutoCutsBase(object):

    def __init__(self, logger):
        super(AutoCutsBase, self).__init__()

        self.logger = logger
        self.kind = 'base'
        self.params = {}

        # funky boolean converter
        self._bool = lambda st: str(st).lower() == 'true'

    def get_params_metadata(self):
        return []
    
    def get_algorithms(self):
        return autocut_methods
    
    def get_autocut_levels(self, image, settings):
        params = settings.get('autocut_params', self.params)
        
        loval, hival = self.calc_cut_levels(image, params=params)
        return loval, hival

    def get_crop(self, data, cropradius=512):
        # Even with numpy, it's kind of slow for some of the autocut
        # methods on a large image, so in those cases we can optionally
        # take a crop of size (radius*2)x(radius*2) from the center of
        # the image and calculate the cut levels on that

        height, width = data.shape[:2]
        x, y = width // 2, height // 2
        if x > cropradius:
            x0 = x - cropradius
            x1 = x0 + cropradius*2
        else:
            x0 = 0
            x1 = width-1
        if y > cropradius:
            y0 = y - cropradius
            y1 = y0 + cropradius*2
        else:
            y0 = 0
            y1 = height-1

        data = data[y0:y1, x0:x1]
        return data
    
    def cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
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

    def calc_cut_levels(self, image, params=None):
        loval, hival = image.get_minmax()

        return (float(loval), float(hival))

    def cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
        return data.clip(vmin, vmax)


class Minmax(AutoCutsBase):

    def __init__(self, logger):
        super(Minmax, self).__init__(logger)
        self.kind = 'minmax'

    def calc_cut_levels(self, image, params=None):
        loval, hival = image.get_minmax()

        return (float(loval), float(hival))

class Histogram(AutoCutsBase):

    def __init__(self, logger):
        super(Histogram, self).__init__(logger)

        self.kind = 'histogram'
        self.params.update(usecrop=True, pct=0.999, numbins=2048)
        
    def get_params_metadata(self):
        return [
            Bunch.Bunch(name='usecrop', type=self._bool,
                        valid=set([True, False]),
                        default=True,
                        description="Use center crop of image for speed"),
            Bunch.Bunch(name='pct', type=float,
                        min=0.0, max=1.0,
                        default=0.999,
                        description="Percentage of the histogram to retain"),
            Bunch.Bunch(name='numbins', type=int,
                        min=100, max=10000,
                        default=2048,
                        description="Number of bins for the histogram"),
            ]
    
    def calc_cut_levels(self, image, params=None):
        data = image.get_data()
        if params == None:
            params = self.params
        
        bnch = self.calc_histogram(data, **params)
        loval, hival = bnch.loval, bnch.hival

        return loval, hival    

    def calc_histogram(self, data, usecrop=True, pct=1.0, numbins=2048):
        if usecrop:
            data = self.get_crop(data)

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

    def __init__(self, logger):
        super(StdDev, self).__init__(logger)

        self.kind = 'stddev'
        # Constants used to calculate the lo and hi cut levels using the
        # "stddev" algorithm (from the old SOSS fits viewer)
        self.params.update(usecrop=True,
                           #hensa_lo=35.0, hensa_hi=90.0,
                           )

    def get_params_metadata(self):
        return [
            Bunch.Bunch(name='usecrop', type=self._bool,
                        valid=set([True, False]),
                        default=True,
                        description="Use center crop of image for speed"),
            ## Bunch.Bunch(name='hensa_lo', type=float, default=35.0,
            ##             description="Low subtraction factor"),
            ## Bunch.Bunch(name='hensa_hi', type=float, default=90.0,
            ##             description="High subtraction factor"),
            ]

    def calc_cut_levels(self, image, params=None):
        data = image.get_data()
        if params == None:
            params = self.params
        loval, hival = self.calc_stddev(data, **params)
        return loval, hival

    def calc_stddev(self, data, usecrop=True, hensa_lo=35.0, hensa_hi=90.0):
        if usecrop:
            data = self.get_crop(data)

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

    def __init__(self, logger):
        super(MedianFilter, self).__init__(logger)

        self.kind = 'median'
        self.params.update(length=7)

    def get_params_metadata(self):
        return [
            Bunch.Bunch(name='usecrop', type=self._bool,
                        valid=set([True, False]),
                        default=True,
                        description="Use center crop of image for speed"),
            Bunch.Bunch(name='length', type=int,
                        default=7,
                        description="Median kernel length"),
            ]

    def calc_cut_levels(self, image, params=None):
        data = image.get_data()
        if params == None:
            params = self.params
        loval, hival = self.calc_medianfilter(data, **params)
        return loval, hival

    def calc_medianfilter(self, data, usecrop=True, length=7):
        if usecrop:
            data = self.get_crop(data)

        xout = scipy.ndimage.filters.median_filter(data, size=length)
        #data_f = numpy.ravel(data)
        #xout = medfilt1(data_f, length)
            
        loval = numpy.nanmin(xout)
        hival = numpy.nanmax(xout)

        return loval, hival


class ZScale(AutoCutsBase):

    def __init__(self, logger):
        super(ZScale, self).__init__(logger)

        self.kind = 'zscale'
        self.params.update(contrast=None, num_points=None, 
                           num_per_row=None)
        
    def get_params_metadata(self):
        return [
            Bunch.Bunch(name='contrast', type=float,
                        default=0.25, allow_none=True,
                        description="Contrast"),
            Bunch.Bunch(name='num_points', type=int,
                        default=600, allow_none=True,
                        description="Number of points to sample"),
            Bunch.Bunch(name='num_per_row', type=int,
                        default=120, allow_none=True,
                        description="Number of points to sample"),
            ]

    def calc_cut_levels(self, image, params=None):
        data = image.get_data()
        if params == None:
            params = self.params
        loval, hival = self.calc_zscale(data, **params)
        return loval, hival

    def calc_zscale(self, data, contrast=None,
                    num_points=None, num_per_row=None):
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

        # calculate contrast parameter, if omitted
        if contrast == None:
            contrast = 0.25

        assert (0.0 < contrast <= 1.0), \
               AutoCutsError("contrast (%.2f) not in range 0 < c <= 1" % (
            contrast))

        # calculate num_points parameter, if omitted
        total_points = numpy.size(data)
        if num_points == None:
            num_points = max(int(total_points * 0.0002), 600)
        num_points = min(num_points, total_points)

        assert (0 < num_points <= total_points), \
               AutoCutsError("num_points not in range 0-%d" % (total_points))

        # calculate num_per_row parameter, if omitted
        if num_per_row == None:
            num_per_row = max(int(0.015 * num_points), 1)
        self.logger.debug("contrast=%.4f num_points=%d num_per_row=%d" % (
            contrast, num_points, num_per_row))

        # sample the data
        num_rows = num_points // num_per_row
        xmax = wd - 1
        xskip = max(xmax // num_per_row, 1)
        ymax = ht-1
        yskip = max(ymax // num_rows, 1)

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

        # zscale fitting function:
        # I(x) = slope * (x - midpoint) + intercept
        def fitting(x, slope, intercept):
            y = slope * (x - midpoint) + intercept
            return y

        # compute a least squares fit 
        X = numpy.array(range(num_pix))
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

            except Exception, e:
                self.logger.debug("curve fitting failed: %s" % (str(e)))
                cov = None
            
        if cov == None:
            self.logger.debug("curve fitting failed")
            return (float(data_min), float(data_max))

        slope, intercept = p

        num_chosen = 0
        self.logger.debug("intercept=%f slope=%f chosen=%d" % (
            intercept, slope, num_chosen))

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


autocuts_table = {
    'clip': Clip,
    'minmax': Minmax,
    'stddev': StdDev,
    'histogram': Histogram,
    'median': MedianFilter,
    'zscale': ZScale,
    }

def get_autocuts(name):
    if not name in autocut_methods:
        raise AutoCutsError("Method '%s' is not supported" % (name))

    return autocuts_table[name]

# END
