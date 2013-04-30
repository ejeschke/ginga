#! /usr/bin/env python
#
# Plot.py -- Plotting function for Ginga FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import numpy

# GUI imports
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

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

    def get_widget(self):
        return self.canvas

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

    def plot(self, xarr, yarr, **kwargs):
        self.set_titles(xtitle=kwargs.pop('xtitle', None),
                        ytitle=kwargs.pop('ytitle', None),
                        title=kwargs.pop('title', None),
                        rtitle=kwargs.pop('rtitle', None))

        kwargs.setdefault('color', None)
        kwargs.setdefault('alpha', 1.0)

        self.ax.plot(xarr, yarr, **kwargs)

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
        self.plot(x, y)


class Cuts(Plot):

    def cuts(self, data, **kwargs):
        """data: pixel values along a line.
        """
        y = data
        x = numpy.arange(len(data))
        self.plot(x, y, **kwargs)


#END
