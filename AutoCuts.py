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

import Bunch

have_scipy = True
autocut_methods = ('minmax', 'median', 'histogram', 'stddev')
try:
    import scipy.ndimage.filters
    #import scipy.misc
except ImportError:
    have_scipy = False
    autocut_methods = ('minmax', 'histogram', 'stddev')

default_autocuts_method = 'histogram'

# Default number of bins to use in the calculation of the autocuts
# histogram for algorithm "histogram"
default_autocuts_bins = 2048

# Default percentage of pixels to keep "inside" the cut, used in 
# the calculation of the autocuts histogram for algorithm "histogram"
default_autocuts_hist_pct = 0.999

# Constants used to calculate the lo and hi cut levels using the
# "stddev" algorithm (from the old SOSS fits viewer)
hensa_lo = 35.0
hensa_hi = 90.0


class AutoCuts(object):

    def __init__(self, logger):
        self.logger = logger

    def get_algorithms(self):
        return autocut_methods
    
    def calc_cut_levels(self, image,
                        method='histogram', pct=None, numbins=None,
                        usecrop=True, cropradius=512):
        if not method:
            method = default_autocuts_method
        if not pct:
            pct = default_autocuts_hist_pct
        if not numbins:
            numbins = default_autocuts_bins

        start_time = time.time()

        if method == 'minmax':
            loval, hival = image.get_minmax()

        else:
            data  = image.get_data()
            # Even with numpy, it's kind of slow to take the distribution
            # on a large image, so if usecrop==True we take
            # a crop of size (radius*2)x(radius*2) from the center of the
            # image and calculate the histogram on that
            if usecrop:
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
            else:
                # Use the full data!
                pass
                
            if method == 'median':
                length = 7
                xout = scipy.ndimage.filters.median_filter(data, size=length)
                #data_f = numpy.ravel(data)
                #xout = medfilt1(data_f, length)

                loval = numpy.nanmin(xout)
                hival = numpy.nanmax(xout)

            elif method == 'stddev':
                # This is the method used in the old SOSS fits viewer
                mdata = numpy.ma.masked_array(data, numpy.isnan(data))
                mean = numpy.mean(mdata)
                sdev = numpy.std(mdata)

                hensa_lo_factor = (hensa_lo - 50.0) / 10.0
                hensa_hi_factor = (hensa_hi - 50.0) / 10.0
                
                loval = hensa_lo_factor * sdev + mean
                hival = hensa_hi_factor * sdev + mean
                
            elif method == 'histogram':
                bnch = self.calc_histogram(data, pct=pct, numbins=numbins)
                loval, hival = bnch.loval, bnch.hival

        end_time = time.time()
        self.logger.debug("cut levels calculation time=%.4f" % (
            end_time - start_time))

        self.logger.debug("lo=%.2f hi=%.2f" % (loval, hival))
        return (loval, hival)

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
        i = numpy.flatnonzero(cumsum > cutoff)[0]
        count_px = cumsum[i]
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
        i = numpy.flatnonzero(cumsum > cutoff)[0]
        count_px = cumsum[i]
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

# END
