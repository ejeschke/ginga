#
# plots.py -- Utility functions for plotting.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

import matplotlib as mpl

from ginga.util import iqcalc as _iqcalc  # Prevent namespace confusion below
from ginga.gw import PlotView

# fix issue of negative numbers rendering incorrectly with default font
mpl.rcParams['axes.unicode_minus'] = False


class Plot(PlotView.CanvasView):

    def __init__(self, figure=None, logger=None, width=500, height=500):
        super().__init__(logger=logger, figure=figure)

        self.logx = False
        self.logy = False

        self.xdata = []
        self.ydata = []

        bd = self.get_bindings()
        bd.enable(pan=False, zoom=False)

    @property
    def fig(self):
        # for backward compatibility
        return self.figure

    def clear(self):
        self.logger.debug('clearing canvas...')
        self.xdata = []
        self.ydata = []
        super().clear()

    def plot(self, xarr, yarr, xtitle=None, ytitle=None, title=None,
             rtitle=None, show_legend=False, **kwdargs):

        if self.logx:
            self.ax.set_xscale('log')
        if self.logy:
            self.ax.set_yscale('log')

        self.xdata = xarr
        self.ydata = yarr

        self.set_titles(xtitle=xtitle, ytitle=ytitle, title=title,
                        rtitle=rtitle)
        self.set_grid(True)
        lines = self.ax.plot(xarr, yarr, **kwdargs)

        self.set_legend(show_legend)

        self.redraw()
        return lines

    def get_data(self):
        return self.figure, self.xdata, self.ydata

    def enable(self, pan=False, zoom=False):
        """If `pan` is True, enable interactive panning in the plot by a
        middle click.  If `zoom` is True , enable interactive zooming in
        the plot by scrolling.
        """
        bd = self.get_bindings()
        bd.enable(pan=pan, zoom=zoom)

    def get_axes_size_in_px(self):
        bbox = self.ax.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= self.figure.dpi
        height *= self.figure.dpi
        return (width, height)

    def set_titles(self, xtitle=None, ytitle=None, title=None,
                   rtitle=None):
        """For backward compatibility -- DO NOT USE -- TO BE DEPRECATED"""
        super().set_titles(title=title, x_axis=xtitle, y_axis=ytitle)

    def set_bg(self, color, ax=None):
        if ax is None:
            ax = self.ax
        ax.set_facecolor(color)

    def autoscale(self, axis):
        """For backward compatibility -- DO NOT USE -- TO BE DEPRECATED"""
        self.zoom_fit()

    def draw(self):
        """For backward compatibility -- DO NOT USE -- TO BE DEPRECATED"""
        return self.redraw()


class HistogramPlot(Plot):

    def histogram(self, data, numbins=2048,
                  xtitle=None, ytitle=None, title=None, rtitle=None):
        minval = np.nanmin(data)
        maxval = np.nanmax(data)

        substval = (minval + maxval) * 0.5
        data[np.isnan(data)] = substval

        dist, bins = np.histogram(data, bins=numbins, density=False)

        # used with 'steps-post' drawstyle, this gives correct histogram-steps
        x = bins
        y = np.append(dist, dist[-1])

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
        x = np.arange(len(data))

        self.plot(x, y, color=color, drawstyle='steps-mid',
                  xtitle=xtitle, ytitle=ytitle, title=title, rtitle=rtitle,
                  alpha=1.0, linewidth=1.0, linestyle='-')


class ContourPlot(Plot):

    def __init__(self, *args, **kwargs):
        super(ContourPlot, self).__init__(*args, **kwargs)

        self.num_contours = 8
        self.cmap = "RdYlGn_r"
        # decent choices: { bicubic | bilinear | nearest }
        self.interpolation = "bilinear"
        self.cbar = None
        self.t_.set(plot_zoom_rate=1.01)

    def _plot_contours(self, x, y, x1, y1, x2, y2, data,
                       num_contours=None):
        # Make a contour plot
        if num_contours is None:
            num_contours = self.num_contours

        ht, wd = data.shape

        self.ax.set_aspect('equal', adjustable='box')
        self.set_titles(title='Contours')

        self.ax.cla()
        self.ax.set_facecolor('#303030')

        try:
            im = self.ax.imshow(data, interpolation=self.interpolation,
                                origin='lower', cmap=self.cmap)

            # Create a contour plot
            self.xdata = np.arange(x1, x2, 1)
            self.ydata = np.arange(y1, y2, 1)
            colors = ['black'] * num_contours
            self.ax.contour(self.xdata, self.ydata, data, num_contours,
                            colors=colors)  # cmap=self.cmap
            # Mark the center of the object
            self.ax.plot([x], [y], marker='x', ms=20.0,
                         color='cyan')

            if self.cbar is None:
                self.cbar = self.figure.colorbar(im, orientation='horizontal',
                                                 shrink=0.8, pad=0.07)
            else:
                vmin, vmax = np.nanmin(data), np.nanmax(data)
                im.set_clim(vmin, vmax)
                self.cbar.update_normal(im)
                self.cbar.update_ticks()

            # Set the pan and zoom position & redraw
            self.set_limits([(x1, y1), (x2, y2)])
            self.set_ranges(x_range=(x1, x2), y_range=(y1, y2))
            self.set_pan(x, y)
            self.redraw()

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


class RadialPlot(Plot):

    def plot_radial(self, x, y, radius, image):

        x, y, radius = int(round(x)), int(round(y)), int(round(radius))
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
            #maxval = np.nanmax(img_data)

            # create arrays of radius and value
            r = []
            v = []
            for i in range(0, wd):
                for j in range(0, ht):
                    r.append(np.sqrt((off_x + i - x) ** 2 +
                                     (off_y + j - y) ** 2))
                    v.append(img_data[j, i])
            r, v = np.array(r), np.array(v)

            # compute and plot radial fitting
            # note: you might wanna change `deg` here.
            coefficients = np.polyfit(x=r, y=v, deg=9)
            polynomial = np.poly1d(coefficients)

            x_curve = np.linspace(np.min(r), np.max(r), len(r))
            y_curve = polynomial(x_curve)

            yerror = 0   # for now, no error bars
            self.ax.errorbar(r, v, yerr=yerror, marker='s', ls='none',
                             mfc='none', mec='#7570b3')
            self.ax.plot(x_curve, y_curve, '-', color='#1b9e77', lw=2)

            self.redraw()

        except Exception as e:
            self.logger.error("Error making radial plot: %s" % (
                str(e)))


class FWHMPlot(Plot):

    def __init__(self, *args, **kwargs):
        super(FWHMPlot, self).__init__(*args, **kwargs)

        self.iqcalc = _iqcalc.IQCalc(self.logger)

    def _plot_fwhm_axis(self, arr, iqcalc, skybg, color1, color2, color3,
                        fwhm_method='gaussian'):
        N = len(arr)
        X = np.array(list(range(N)))
        Y = arr
        # subtract sky background
        Y = Y - skybg
        maxv = Y.max()
        # clamp to 0..max
        Y = Y.clip(0, maxv)
        self.logger.debug("Y=%s" % (str(Y)))
        self.ax.plot(X, Y, color=color1, marker='.')

        res = iqcalc.calc_fwhm(arr, medv=skybg, method_name=fwhm_method)
        fwhm, mu = res.fwhm, res.mu

        # Make a little smoother fitted curve by plotting intermediate
        # points
        XN = np.linspace(0.0, float(N), N * 10)
        Z = np.array([res.fit_fn(x, res.fit_args) for x in XN])
        self.ax.plot(XN, Z, color=color1, linestyle=':')
        self.ax.axvspan(mu - fwhm * 0.5, mu + fwhm * 0.5,
                        facecolor=color3, alpha=0.25)
        return fwhm

    def plot_fwhm(self, x, y, radius, image, cutout_data=None,
                  iqcalc=None, fwhm_method='gaussian'):

        x, y, radius = int(round(x)), int(round(y)), int(round(radius))
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

            skybg = np.ma.median(cutout_data)
            self.logger.debug("cutting x=%d y=%d r=%d med=%f" % (
                x, y, radius, skybg))

            self.logger.debug("xarr=%s" % (str(xarr)))
            fwhm_x = self._plot_fwhm_axis(xarr, iqcalc, skybg,
                                          '#7570b3', '#7570b3', 'purple',
                                          fwhm_method=fwhm_method)

            self.logger.debug("yarr=%s" % (str(yarr)))
            fwhm_y = self._plot_fwhm_axis(yarr, iqcalc, skybg,
                                          '#1b9e77', '#1b9e77', 'seagreen',
                                          fwhm_method=fwhm_method)

            falg = fwhm_method
            self.ax.legend(('data x', '%s x' % falg, 'data y', '%s y' % falg),
                           loc='upper right', shadow=False, fancybox=False,
                           prop={'size': 8}, labelspacing=0.2)
            self.set_titles(title="FWHM X: %.2f  Y: %.2f" % (fwhm_x, fwhm_y))

            self.redraw()

        except Exception as e:
            self.logger.error("Error making fwhm plot: %s" % (
                str(e)))

    def plot_fwhm_data(self, x, y, radius, arr_data,
                       iqcalc=None, fwhm_method='gaussian'):

        x, y, radius = int(round(x)), int(round(y)), int(round(radius))

        if iqcalc is None:
            iqcalc = self.iqcalc

        x0, y0, xarr, yarr = iqcalc.cut_cross(x, y, radius, arr_data)

        self.ax.cla()

        self.set_titles(ytitle='Brightness', xtitle='Pixels', title='FWHM')
        self.ax.grid(True)

        # Make a FWHM plot
        try:
            # get median value from the cutout area
            skybg = np.ma.median(arr_data)
            self.logger.debug("cutting x=%d y=%d r=%d med=%f" % (
                x, y, radius, skybg))

            self.logger.debug("xarr=%s" % (str(xarr)))
            fwhm_x = self._plot_fwhm_axis(xarr, iqcalc, skybg,
                                          '#7570b3', '#7570b3', 'purple',
                                          fwhm_method=fwhm_method)

            self.logger.debug("yarr=%s" % (str(yarr)))
            fwhm_y = self._plot_fwhm_axis(yarr, iqcalc, skybg,
                                          '#1b9e77', '#1b9e77', 'seagreen',
                                          fwhm_method=fwhm_method)

            falg = fwhm_method
            self.ax.legend(('data x', '%s x' % falg, 'data y', '%s y' % falg),
                           loc='upper right', shadow=False, fancybox=False,
                           prop={'size': 8}, labelspacing=0.2)
            self.set_titles(title="FWHM X: %.2f  Y: %.2f" % (fwhm_x, fwhm_y))

            self.redraw()

        except Exception as e:
            self.logger.error("Error making fwhm plot: {}".format(e))


class EEPlot(Plot):
    """Class to handle plotting of encircled and ensquared energy (EE) values."""

    def plot_ee(self, encircled_energy_function=None,
                ensquared_energy_function=None, sampling_radius=None,
                total_radius=None):
        """
        Parameters
        ----------
        encircled_energy_function, ensquared_energy_function : obj or `None`
            Interpolation function from ``scipy.interpolate.interp1d`` for
            encircled and ensquared energy (EE) values, respectively.
            If not given, will skip plotting but at least one needs to be given.

        sampling_radius : float or `None`
            Show radius for sampling of EE, if desired.

        total_radius : float or `None`
            Show radius where EE is expected to be 1, if desired.

        """
        if (encircled_energy_function is None and
                ensquared_energy_function is None):
            raise ValueError('At least one EE function must be provided')

        self.ax.cla()
        self.ax.grid(True)

        x_max = 0
        title = ''
        d = {}

        if encircled_energy_function:
            d['Encircled Energy'] = {'func': encircled_energy_function,
                                     'color': '#7570b3',
                                     'marker': 's',
                                     'title_pfx': 'EE(circ)'}
        if ensquared_energy_function:
            d['Ensquared Energy'] = {'func': ensquared_energy_function,
                                     'color': '#1b9e77',
                                     'marker': 'x',
                                     'title_pfx': 'EE(sq)'}

        for key, val in d.items():
            func = val['func']
            color = val['color']
            x = func.x
            y = func.y
            x_max = max(x.max(), x_max)
            self.ax.plot(x, y, color=color, marker=val['marker'], mfc='none',
                         mec=color, label=key)
            if total_radius and not title:
                self.ax.axvline(total_radius, color='k', ls='--')
            if sampling_radius:
                if title:
                    title += ', '
                else:
                    self.ax.axvline(sampling_radius, color='k', ls='--')
                ys = func(sampling_radius)
                title += f"{val['title_pfx']}={ys:.3f}"
                self.ax.plot(sampling_radius, ys, marker='o', ls='none',
                             mfc=color, mec=color, label=None)

        self.set_titles(title=title, xtitle='Radius [pixels]', ytitle='EE')
        self.ax.set_xlim(-0.1, x_max)
        self.ax.legend(loc='lower right', shadow=False, fancybox=False,
                       prop={'size': 8}, labelspacing=0.2)
        self.redraw()


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
        X = np.arange(x1, x2, 1)
        Y = np.arange(y1, y2, 1)
        X, Y = np.meshgrid(X, Y)

        try:
            from mpl_toolkits.mplot3d import Axes3D  # noqa
            from matplotlib.ticker import LinearLocator, FormatStrFormatter

            self.ax = self.figure.gca(projection='3d', facecolor='#808080')

            self.set_titles(ytitle='Y', xtitle='X',
                            title='Surface Plot')
            self.ax.grid(True)

            zmin = np.min(Z) if self.floor is None else self.floor
            zmax = np.max(Z) if self.ceiling is None else self.ceiling

            sfc = self.ax.plot_surface(X, Y, Z, rstride=self.stride,
                                       cstride=self.stride,
                                       cmap=self.cmap, linewidth=0,
                                       antialiased=False)

            # TODO: need to determine sensible defaults for these based
            # on the data
            self.ax.zaxis.set_major_locator(LinearLocator(10))
            self.ax.zaxis.set_major_formatter(FormatStrFormatter('%.0f'))
            self.ax.set_zlim(zmin, zmax)

            self.ax.xaxis.set_ticks(np.arange(x1, x2, 10))
            self.ax.xaxis.set_major_formatter(FormatStrFormatter('%.0f'))
            self.ax.yaxis.set_ticks(np.arange(y1, y2, 10))
            self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))

            self.ax.view_init(elev=20.0, azim=30.0)

            self.figure.colorbar(sfc, orientation='horizontal', shrink=0.9,
                                 pad=0.01)

            self.redraw()

        except Exception as e:
            self.logger.error("Error making surface plot: %s" % (
                str(e)))

# END
