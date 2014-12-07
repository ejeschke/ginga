#
# PlotBase.py -- Plotting function for Gen2 FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import numpy

import matplotlib

from ginga.misc import Callback

class PlotBase(Callback.Callbacks):

    def __init__(self, logger, figureCanvasClass, dpi=100,
                 width=2, height=2):
        Callback.Callbacks.__init__(self)

        self.logger = logger

        # For callbacks
        for name in ('close', ):
            self.enable_callback(name)

        self.fig = matplotlib.figure.Figure(figsize=(width, height),
                                            dpi=dpi)
        self.canvas = figureCanvasClass(self.fig)
        self.ax = None

        self.logx = False
        self.logy = False

    def get_widget(self):
        return self.canvas

    def _sanity_check_window(self):
        pass

    def add_axis(self, **kwdargs):
        self.ax = self.fig.add_subplot(111, **kwdargs)
        return self.ax
        
    def get_axis(self):
        return self.ax

    def set_titles(self, xtitle=None, ytitle=None, title=None,
                   rtitle=None):
        self._sanity_check_window()
        if xtitle is not None:
            self.ax.set_xlabel(xtitle)
        if ytitle is not None:
            self.ax.set_ylabel(ytitle)
        if title is not None:
            self.ax.set_title(title)
        if rtitle is not None:
            pass

    def clear(self):
        self._sanity_check_window()
        self.logger.debug('clearing canvas...')
        self.ax.cla()

    def show(self):
        self._sanity_check_window()
        self.logger.debug('raising window...')
        self.canvas.show()

    def hide(self):
        self._sanity_check_window()
        self.logger.debug('hiding window...')
        pass

    def close(self):
        self.logger.debug('closing window....')
        self.canvas.destroy()

        self.make_callback('close')
        return False

    def _draw(self):
        self.fig.canvas.draw()

    def plot(self, xarr, yarr, xtitle=None, ytitle=None, title=None,
             rtitle=None, **kwdargs):
        if self.logx:
            self.ax.set_xscale('log')
        if self.logy:
            self.ax.set_yscale('log')

        self.set_titles(xtitle=xtitle, ytitle=ytitle, title=title,
                        rtitle=rtitle)
        self.ax.grid(True)
        self.ax.plot(xarr, yarr, **kwdargs)

        self._draw()


class HistogramMixin(object):

    def histogram(self, data, numbins=2048,
                  xtitle=None, ytitle=None, title=None, rtitle=None):
        minval = numpy.nanmin(data)
        maxval = numpy.nanmax(data)

        substval = (minval + maxval)/2.0
        data[numpy.isnan(data)] = substval

        dist, bins = numpy.histogram(data, bins=numbins, density=False)

        # used with 'steps-post' drawstyle, this gives correct histogram-steps
        x = bins
        y = numpy.append(dist, dist[-1])

        self.clear()
        self.plot(x, y, alpha=1.0, linewidth=1.0, linestyle='-',
                  xtitle=xtitle, ytitle=ytitle, title=title, rtitle=rtitle,
                  drawstyle='steps-post')


class CutsMixin(object):

    def cuts(self, data,
             xtitle=None, ytitle=None, title=None, rtitle=None,
             color=None):
        """data: pixel values along a line.
        """
        y = data
        x = numpy.arange(len(data))

        self.plot(x, y, color=color, drawstyle='steps-mid',
                  xtitle=xtitle, ytitle=ytitle, title=title, rtitle=rtitle,
                  alpha=1.0, linewidth=1.0, linestyle='-')


#END
