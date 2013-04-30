#
# Plot.py -- Plotting function for Gen2 FITS viewer.
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

# GUI imports
import gtk

import matplotlib
matplotlib.use('GTKCairo')
from  matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo \
     as FigureCanvas
import pango

from ginga.misc import Callback

class Plot(Callback.Callbacks):

    def __init__(self, logger):
        Callback.Callbacks.__init__(self)

        self.logger = logger

        # For callbacks
        for name in ('close', ):
            self.enable_callback(name)

        self.fig = matplotlib.figure.Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('X values')
        self.ax.set_ylabel('Y values')
        self.ax.set_title('')
        self.ax.grid(True)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.show_all()

    def get_widget(self):
        return self.canvas
    
    def getAxis(self):
        return self.ax
    
    def _sanity_check_window(self):
        pass

    def set_titles(self, xtitle=None, ytitle=None, title=None,
                   rtitle=None):
        self._sanity_check_window()
        if xtitle != None:
            self.ax.set_xlabel(xtitle)
        if ytitle != None:
            self.ax.set_ylabel(ytitle)
        if title != None:
            self.ax.set_title(title)
        if rtitle != None:
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
        self.set_titles(xtitle=xtitle, ytitle=ytitle, title=title,
                        rtitle=rtitle)
        self.ax.plot(xarr, yarr, **kwdargs)
        self.ax.grid(True)
        self._draw()
        

class Histogram(Plot):

    def histogram(self, data, numbins=2048,
                  xtitle=None, ytitle=None, title=None, rtitle=None):
        minval = numpy.nanmin(data)
        maxval = numpy.nanmax(data)

        substval = (minval + maxval)/2.0
        data[numpy.isnan(data)] = substval

        dist, bins = numpy.histogram(data, bins=numbins, density=False)

        x = bins[:-1]
        y = dist
        self.clear()
        self.set_titles(xtitle=xtitle, ytitle=ytitle, title=title,
                        rtitle=rtitle)
        self.plot(x, y, alpha=1.0, linewidth=1.0, linestyle='-')


class Cuts(Plot):

    def cuts(self, data,
             xtitle=None, ytitle=None, title=None, rtitle=None,
             color=None):
        """data: pixel values along a line.
        """
        y = data
        x = numpy.arange(len(data))
        #self.clear()
        self.set_titles(xtitle=xtitle, ytitle=ytitle, title=title,
                        rtitle=rtitle)
        self.plot(x, y, color=color, drawstyle='steps-mid',
                  alpha=1.0, linewidth=1.0, linestyle='-')


#END
