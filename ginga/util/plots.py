#
# plots.py -- Utility functions for plotting.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
import matplotlib as mpl
from matplotlib.figure import Figure
# fix issue of negative numbers rendering incorrectly with default font
mpl.rcParams['axes.unicode_minus'] = False

from ginga.util import iqcalc
from ginga.misc import Callback

class Plot(Callback.Callbacks):

    def __init__(self, figure=None, logger=None, width=500, height=500):
        Callback.Callbacks.__init__(self)

        if figure is None:
            figure = Figure()
            dpi = figure.get_dpi()
            if dpi is None or dpi < 0.1:
                dpi = 100
            wd_in, ht_in = float(width)/dpi, float(height)/dpi
            figure.set_size_inches(wd_in, ht_in)
        self.fig = figure
        if hasattr(self.fig, 'set_tight_layout'):
            self.fig.set_tight_layout(True)
        self.logger = logger
        self.fontsize = 10
        self.ax = None

        self.logx = False
        self.logy = False

        self.xdata = []
        self.ydata = []

        # For callbacks
        for name in ('draw-canvas', ):
            self.enable_callback(name)

    def get_figure(self):
        return self.fig

    def get_widget(self):
        return self.fig.canvas

    def add_axis(self, **kwdargs):
        self.ax = self.fig.add_subplot(111, **kwdargs)
        return self.ax

    def get_axis(self):
        return self.ax

    def set_axis(self, ax):
        self.ax = ax

    def set_titles(self, xtitle=None, ytitle=None, title=None,
                   rtitle=None):
        if xtitle is not None:
            self.ax.set_xlabel(xtitle)
        if ytitle is not None:
            self.ax.set_ylabel(ytitle)
        if title is not None:
            self.ax.set_title(title)
        if rtitle is not None:
            pass
        ax = self.ax
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
             ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(self.fontsize)

    def clear(self):
        self.logger.debug('clearing canvas...')
        self.ax.cla()
        self.xdata = []
        self.ydata = []

    def draw(self):
        self.fig.canvas.draw()

        self.make_callback('draw-canvas')

    def plot(self, xarr, yarr, xtitle=None, ytitle=None, title=None,
             rtitle=None, **kwdargs):

        if self.ax is None:
            self.add_axis()

        if self.logx:
            self.ax.set_xscale('log')
        if self.logy:
            self.ax.set_yscale('log')

        self.xdata = xarr
        self.ydata = yarr

        self.set_titles(xtitle=xtitle, ytitle=ytitle, title=title,
                        rtitle=rtitle)
        self.ax.grid(True)
        self.ax.plot(xarr, yarr, **kwdargs)

        for item in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            item.set_fontsize(self.fontsize)

        # Make x axis labels a little more readable
        lbls = self.ax.xaxis.get_ticklabels()
        for lbl in lbls:
            lbl.set(rotation=45, horizontalalignment='right')

        #self.fig.tight_layout()

        self.draw()

    def get_data(self):
            return self.fig, self.xdata, self.ydata

class HistogramPlot(Plot):

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


class CutsPlot(Plot):

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


class ContourPlot(Plot):

    def __init__(self, *args, **kwargs):
        super(ContourPlot, self).__init__(*args, **kwargs)

        self.num_contours = 8
        self.plot_panx = 0
        self.plot_pany = 0
        self.plot_zoomlevel = 1.0
        self.cmap = "RdYlGn_r"
        # decent choices: { bicubic | bilinear | nearest }
        self.interpolation = "bilinear"
        self.cbar = None

    def connect_zoom_callbacks(self):
        canvas = self.fig.canvas
        connect = canvas.mpl_connect
        # These are not ready for prime time...
        # connect("motion_notify_event", self.plot_motion_notify)
        # connect("button_press_event", self.plot_button_press)
        connect("scroll_event", self.plot_scroll)

    def _plot_contours(self, x, y, x1, y1, x2, y2, data,
                       num_contours=None):
        # Make a contour plot
        if num_contours is None:
            num_contours = self.num_contours

        if self.ax is None:
            self.add_axis()

        ht, wd = data.shape

        self.ax.set_aspect('equal', adjustable='box')
        self.set_titles(title='Contours')
        #self.fig.tight_layout()

        # Set pan position in contour plot
        self.plot_panx = float(x) / wd
        self.plot_pany = float(y) / ht

        if self.cbar is not None:
            self.cbar.remove()

        self.ax.cla()
        self.ax.set_axis_bgcolor('#303030')

        try:
            im = self.ax.imshow(data, interpolation=self.interpolation,
                                origin='lower', cmap=self.cmap)

            # Create a contour plot
            self.xdata = numpy.arange(x1, x2, 1)
            self.ydata = numpy.arange(y1, y2, 1)
            colors = [ 'black' ] * num_contours
            cs = self.ax.contour(self.xdata, self.ydata, data, num_contours,
                                 colors=colors
                                 #cmap=self.cmap
                                 )
            ## self.ax.clabel(cs, inline=1, fontsize=10,
            ##                fmt='%5.3f', color='cyan')
            # Mark the center of the object
            self.ax.plot([x], [y], marker='x', ms=20.0,
                         color='cyan')

            self.cbar = self.fig.colorbar(im, orientation='horizontal',
                                          shrink=0.8, pad=0.07)
            # Set the pan and zoom position & redraw
            self.plot_panzoom()

        except Exception as e:
            self.logger.error("Error making contour plot: %s" % (
                str(e)))

    def plot_contours_data(self, x, y, data, num_contours=None):
        ht, wd = data.shape
        self._plot_contours(x, y, 0, 0, wd, ht, data,
                            num_contours=num_contours)

    def plot_contours(self, x, y, radius, image, num_contours=None):
        img_data, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)

        ## self._plot_contours(x, y, x1, y1, x2, y2, img_data,
        ##                     num_contours=num_contours)
        cx, cy = x - x1, y - y1
        self.plot_contours_data(cx, cy, img_data,
                            num_contours=num_contours)

    def plot_panzoom(self):
        ht, wd = len(self.ydata), len(self.xdata)
        x = int(self.plot_panx * wd)
        y = int(self.plot_pany * ht)

        if self.plot_zoomlevel >= 1.0:
            scalefactor = 1.0 / self.plot_zoomlevel
        elif self.plot_zoomlevel < -1.0:
            scalefactor = - self.plot_zoomlevel
        else:
            # wierd condition?--reset to 1:1
            scalefactor = 1.0
            self.plot_zoomlevel = 1.0

        xdelta = int(scalefactor * (wd/2.0))
        ydelta = int(scalefactor * (ht/2.0))
        xlo, xhi = x-xdelta, x+xdelta
        # distribute remaining x space from plot
        if xlo < 0:
            xsh = abs(xlo)
            xlo, xhi = 0, min(wd-1, xhi+xsh)
        elif xhi >= wd:
            xsh = xhi - wd
            xlo, xhi = max(0, xlo-xsh), wd-1
        self.ax.set_xlim(xlo, xhi)

        ylo, yhi = y-ydelta, y+ydelta
        # distribute remaining y space from plot
        if ylo < 0:
            ysh = abs(ylo)
            ylo, yhi = 0, min(ht-1, yhi+ysh)
        elif yhi >= ht:
            ysh = yhi - ht
            ylo, yhi = max(0, ylo-ysh), ht-1
        self.ax.set_ylim(ylo, yhi)

        self.draw()

    def plot_zoom(self, val):
        self.plot_zoomlevel = val
        self.plot_panzoom()

    def plot_scroll(self, event):
        # Matplotlib only gives us the number of steps of the scroll,
        # positive for up and negative for down.
        direction = None
        if event.step > 0:
            #delta = 0.9
            self.plot_zoomlevel += 1.0
        elif event.step < 0:
            #delta = 1.1
            self.plot_zoomlevel -= 1.0

        self.plot_panzoom()

        # x1, x2 = self.ax.get_xlim()
        # y1, y2 = self.ax.get_ylim()
        # self.ax.set_xlim(x1*delta, x2*delta)
        # self.ax.set_ylim(y1*delta, y2*delta)
        # self.draw()
        return True

    def plot_button_press(self, event):
        if event.button == 1:
            self.plot_x, self.plot_y = event.x, event.y
        return True

    def plot_motion_notify(self, event):
        if event.button == 1:
            xdelta = event.x - self.plot_x
            #ydelta = event.y - self.plot_y
            ydelta = self.plot_y - event.y
            self.pan_plot(xdelta, ydelta)

    def pan_plot(self, xdelta, ydelta):
        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_ylim()

        self.ax.set_xlim(x1+xdelta, x2+xdelta)
        self.ax.set_ylim(y1+ydelta, y2+ydelta)

        self.draw()


class RadialPlot(Plot):

    def plot_radial(self, x, y, radius, image):

        img_data, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)

        self.ax.cla()

        # Make a radial plot
        self.ax.set_xlim(-0.1, radius)

        self.set_titles(title="Radial plot", xtitle='Radius [pixels]',
                        ytitle='Pixel Value (ADU)')
        self.ax.grid(True)

        try:
            ht, wd = img_data.shape
            off_x, off_y = x1, y1
            maxval = numpy.nanmax(img_data)

            # create arrays of radius and value
            r = []
            v = []
            for i in range(0, wd):
                for j in range(0, ht):
                    r.append( numpy.sqrt( (off_x + i - x)**2 + (off_y + j - y)**2 ) )
                    v.append(img_data[j, i])
            r, v = numpy.array(r), numpy.array(v)

            # compute and plot radial fitting
            # note: you might wanna change `deg` here.
            coefficients = numpy.polyfit(x=r, y=v, deg=10)
            polynomial = numpy.poly1d(coefficients)

            x_curve = numpy.linspace(numpy.min(r), numpy.max(r), len(r))
            y_curve = polynomial(x_curve)

            yerror = 0   # for now, no error bars
            self.ax.errorbar(r, v, yerr=yerror, marker='x', ls='none',
                             color='blue')
            self.ax.plot(x_curve, y_curve, '-', color='green', lw=2)

            #self.fig.tight_layout()

            self.draw()

        except Exception as e:
            self.logger.error("Error making radial plot: %s" % (
                str(e)))

class FWHMPlot(Plot):

    def __init__(self, *args, **kwargs):
        super(FWHMPlot, self).__init__(*args, **kwargs)

        self.iqcalc = iqcalc.IQCalc(self.logger)

    def _plot_fwhm_axis(self, arr, iqcalc, skybg, color1, color2, color3):
        N = len(arr)
        X = numpy.array(list(range(N)))
        Y = arr
        # subtract sky background
        Y = Y - skybg
        maxv = Y.max()
        # clamp to 0..max
        Y = Y.clip(0, maxv)
        self.logger.debug("Y=%s" % (str(Y)))
        self.ax.plot(X, Y, color=color1, marker='.')

        fwhm, mu, sdev, maxv = iqcalc.calc_fwhm(arr)
        # Make a little smoother gaussian curve by plotting intermediate
        # points
        XN = numpy.linspace(0.0, float(N), N*10)
        Z = numpy.array([iqcalc.gaussian(x, (mu, sdev, maxv))
                         for x in XN])
        self.ax.plot(XN, Z, color=color1, linestyle=':')
        self.ax.axvspan(mu-fwhm/2.0, mu+fwhm/2.0,
                           facecolor=color3, alpha=0.25)
        return (fwhm, mu, sdev, maxv)

    def plot_fwhm(self, x, y, radius, image, cutout_data=None, iqcalc=None):

        x0, y0, xarr, yarr = image.cutout_cross(x, y, radius)

        if iqcalc is None:
            iqcalc = self.iqcalc

        self.ax.cla()

        #self.ax.set_aspect('equal', adjustable='box')
        self.set_titles(ytitle='Brightness', xtitle='Pixels',
                        title='FWHM')
        self.ax.grid(True)

        # Make a FWHM plot
        try:
            # get median value from the cutout area
            if cutout_data is None:
                cutout_data, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)

            skybg = numpy.median(cutout_data)
            self.logger.debug("cutting x=%d y=%d r=%d med=%f" % (
                x, y, radius, skybg))

            self.logger.debug("xarr=%s" % (str(xarr)))
            fwhm_x, mu, sdev, maxv = self._plot_fwhm_axis(xarr, iqcalc, skybg,
                                                          'blue', 'blue', 'skyblue')

            self.logger.debug("yarr=%s" % (str(yarr)))
            fwhm_y, mu, sdev, maxv = self._plot_fwhm_axis(yarr, iqcalc, skybg,
                                                          'green', 'green', 'seagreen')

            self.ax.legend(('data x', 'gauss x', 'data y', 'gauss y'),
                           loc='upper right', shadow=False, fancybox=False,
                           prop={'size': 8}, labelspacing=0.2)
            self.set_titles(title="FWHM X: %.2f  Y: %.2f" % (fwhm_x, fwhm_y))

            #self.fig.tight_layout()

            self.draw()

        except Exception as e:
            self.logger.error("Error making fwhm plot: %s" % (
                str(e)))


class SurfacePlot(Plot):

    def __init__(self, *args, **kwargs):
        super(SurfacePlot, self).__init__(*args, **kwargs)

        self.dx = 21
        self.dy = 21
        self.floor = None
        self.ceiling = None
        self.stride = 1
        self.cmap = "RdYlGn_r"

    def plot_surface(self, x, y, radius, image, cutout_data=None):

        Z, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)
        X = numpy.arange(x1, x2, 1)
        Y = numpy.arange(y1, y2, 1)
        X, Y = numpy.meshgrid(X, Y)

        try:
            from mpl_toolkits.mplot3d import Axes3D
            from matplotlib.ticker import LinearLocator, FormatStrFormatter

            self.ax = self.fig.gca(projection='3d', axisbg='#808080')
            self.ax.set_aspect('equal', adjustable='box')
            #self.ax.cla()

            self.set_titles(ytitle='Y', xtitle='X',
                            title='Surface Plot')
            self.ax.grid(True)

            zmin = numpy.min(Z) if self.floor is None else self.floor
            zmax = numpy.max(Z) if self.ceiling is None else self.ceiling

            sfc = self.ax.plot_surface(X, Y, Z, rstride=self.stride,
                                       cstride=self.stride,
                                       cmap=self.cmap, linewidth=0,
                                       antialiased=False)

            # TODO: need to determine sensible defaults for these based
            # on the data
            self.ax.zaxis.set_major_locator(LinearLocator(10))
            self.ax.zaxis.set_major_formatter(FormatStrFormatter('%.0f'))
            self.ax.set_zlim(zmin, zmax)

            self.ax.xaxis.set_ticks(numpy.arange(x1, x2, 10))
            self.ax.xaxis.set_major_formatter(FormatStrFormatter('%.0f'))
            self.ax.yaxis.set_ticks(numpy.arange(y1, y2, 10))
            self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))

            self.ax.view_init(elev=20.0, azim=30.0)

            self.fig.colorbar(sfc, orientation='horizontal', shrink=0.9,
                              pad=0.01)

            self.draw()

        except Exception as e:
            self.logger.error("Error making surface plot: %s" % (
                str(e)))

#END
