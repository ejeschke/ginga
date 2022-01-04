#! /usr/bin/env python3
#
"""
Plot time series data in an interactive plot viewer.

Usage
=====
$ python3 plot_time_series.py --loglevel=20 --stderr

Plots add new data every second, and update on screen every 5 sec.
24 hours of data is kept.  Each plot starts out in "autoaxis X PAN"
and "autoaxis Y VIS".

Things you can do in a plot:

1) Scroll the mouse wheel to zoom the X axis

2) Hold CTRL and scroll the mouse wheel to zoom the Y axis.

3) Press 'y' to autozoom the Y axis to the full range of the Y data.
   (The message "Autoaxis Y ON" should appear briefly).
   Press 'y' again to toggle off this behavior.

4) Press 'v' to autozoom the Y axis to the range of the *visible* data shown
   (The message "Autoaxis Y VIS" should appear briefly).
   Press 'v' again to toggle off this behavior.

5) Press 'x' to autozoom the X axis to the full range of the X data
   (The message "Autoaxis X ON" should appear briefly).
   Press 'x' again to toggle off this behavior.

6) Press 'p' to autopan the X axis to always show the latest data on
   the right (the message "Autoaxis X PAN" should appear briefly).
   Press 'p' again to toggle off this behavior.
.
"""
import sys
import time
import threading

import numpy as np

import ginga.toolkit as ginga_toolkit
from ginga.misc import log, Bunch
from ginga.plot.plotaide import PlotAide
import ginga.plot.data_source as dsp

win_wd, win_ht = 800, 280


class FakeData:
    """Generate fake time-series data."""

    def __init__(self, name, t_start, y_range, num_pts):
        self.name = name
        self.t_start = t_start
        self.y_range = y_range
        self.num_pts = num_pts
        self.data_src = None
        self.tv = 0.0
        self.tv_dir = 'up'
        self.tv_dct = {0: 'up', 1: 'down'}
        self.tv_delta = 0.1
        self.tv_dmin = 1.0
        self.tv_dmax = 30.0
        self.tv_deadline = time.time()

    def rand_rng(self, a, b):
        return (b - a) * np.random.random_sample() + a

    def generate_point(self, t):
        x, y = t, self.tv

        if self.tv_dir == 'up':
            y = self.rand_rng(y, min(y + self.tv_delta, self.y_range[1]))
        else:
            y = self.rand_rng(max(y - self.tv_delta, self.y_range[0]), y)
        self.tv = y
        if t >= self.tv_deadline:
            v = np.random.randint(0, 2)
            self.tv_dir = self.tv_dct[v]
            self.tv_deadline = t + self.rand_rng(self.tv_dmin, self.tv_dmax)

        ## p = np.random.randint(0, 100)
        ## if p >= 98:
        ##     y = np.nan
        return (x, y)

    def init_points(self, data_src, start=None):
        N, t = self.num_pts, self.t_start
        if start is None:
            start = (self.y_range[0] + self.y_range[1]) * 0.5
        self.tv = start
        self.tv_deadline = t - N + self.rand_rng(self.tv_dmin, self.tv_dmax)
        points = np.array([self.generate_point(ti)
                           for ti in np.arange(t - N, t, 1.0)])
        data_src.set_points(points)
        self.data_src = data_src

    def add_point(self, t):
        pt = self.generate_point(t)
        self.data_src.add(pt)
        return pt


def timer1_cb(timer, fdg_l, interval):
    t = time.time()
    timer.set(interval)

    for fdg in fdg_l:
        fdg.add_point(t)
        dsp.update_plot_from_source(fdg.data_src, fdg.data_src.plot,
                                    update_limits=True)


def timer2_cb(timer, app, aides, fdg_l, interval):
    timer.set(interval)

    for a in aides:
        # keep plots responsive
        app.process_events()
        a.aide.update_plots()


def make_plot(logger, dims, sources, y_rng, y_acc=np.mean,
              title='', warn_y=None, alert_y=None,
              show_x_axis=True, show_y_axis=True):

    from ginga.gw import Viewers
    from ginga.canvas.types import plots as gplots
    import ginga.plot.time_series as tsp

    win_wd, win_ht = dims[:2]
    viewer = Viewers.CanvasView(logger, render='widget')

    viewer.set_desired_size(win_wd, win_ht)
    viewer.set_zoom_algorithm('rate')
    viewer.set_zoomrate(1.41)
    viewer.enable_autozoom('off')
    viewer.set_background('white')
    viewer.set_foreground('black')
    viewer.set_enter_focus(True)

    # our plot
    aide = PlotAide(viewer)
    aide.settings.set(autoaxis_x='pan', autoaxis_y='vis')

    bg = tsp.TimePlotBG(warn_y=warn_y, alert_y=alert_y, linewidth=2)
    aide.add_plot_decor(bg)

    title = tsp.TimePlotTitle(title=title)
    aide.add_plot_decor(title)

    x_axis = tsp.XTimeAxis(num_labels=4)
    aide.add_plot_decor(x_axis)

    y_axis = gplots.YAxis(num_labels=4)
    aide.add_plot_decor(y_axis)

    colors = ['purple', 'palegreen4', 'red', 'brown', 'blue']

    for i, src in enumerate(sources):
        psrc = gplots.XYPlot(name=src.name, color=colors[i % len(colors)],
                             x_acc=np.mean, y_acc=y_acc,
                             linewidth=2.0, coord='data')
        buf = np.zeros((src.num_pts, 2), dtype=float)
        dsrc = dsp.XYDataSource(buf, none_for_empty=True, overwrite=True)
        dsrc.plot = psrc
        src.init_points(dsrc)

        aide.add_plot(psrc)
        dsp.update_plot_from_source(dsrc, psrc, update_limits=True)

    # initially, show last 4 hours worth of data.
    t, _ = dsrc.get_latest()
    aide.zoom_limit_x(t - 4 * 3600, t)

    # add scrollbar interface around this viewer
    si = Viewers.GingaScrolledViewerWidget(viewer=viewer, width=win_wd,
                                           height=win_ht)
    aide.configure_scrollbars(si)

    res = Bunch.Bunch(viewer=viewer, aide=aide, widget=si)
    return res


def make_data(t, N, names, y_range):
    srcs = []
    for i, name in enumerate(names):
        fdg = FakeData(name, t, y_range, N)
        srcs.append(fdg)

    return srcs


def cross_connect_plots(plot_info):
    # cross connect the plots so that zooming or panning in X in one
    # does the same to all the others
    m_settings = plot_info[0].aide.settings
    for res_a in plot_info:
        for res_b in set(plot_info) - set([res_a]):
            res_a.aide.add_callback('plot-zoom-x', res_b.aide.plot_zoom_x_cb)

        if res_a.aide.settings is not m_settings:
            m_settings.share_settings(res_a.aide.settings, keylist=['autoaxis_x'])


def main(options, args):

    logger = log.get_logger("example1", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    # now we can import
    from ginga.gw import Widgets

    def quit(self, *args):
        logger.info("Top window closed.")
        sys.exit()

    ev_quit = threading.Event()

    app = Widgets.Application(logger=logger)
    app.add_callback('shutdown', quit)

    w = app.make_window("EnvMon")
    w.add_callback('close', quit)

    vbox = Widgets.VBox()
    vbox.set_spacing(1)

    dims = (win_wd, win_ht)

    # default: data every second for 24 hours
    N = options.numvalues
    M = options.numplots
    t = time.time()
    plots = []
    fdgs = []

    # make a plot of outside and dome wind speed
    y_rng = (0.0, 50.0)
    srcs = make_data(t, N, ["Outside", "Dome"], y_rng)
    fdgs.extend(srcs)
    res = make_plot(logger, dims, srcs, y_rng,
                    y_acc=np.mean, title="Wind Speed (m/s)")
    vbox.add_widget(res.widget, stretch=1)
    plots.append(res)

    # make a plot of outside and dome temperature
    y_rng = (-30.0, 50.0)
    srcs = make_data(t, N, ["Outside", "Dome"], y_rng)
    fdgs.extend(srcs)
    res = make_plot(logger, dims, srcs, y_rng,
                    y_acc=np.mean, title="Temperature (C)")
    vbox.add_widget(res.widget, stretch=1)
    plots.append(res)

    # make a plot of outside and dome humidity
    y_rng = (0.0, 100.0)
    srcs = make_data(t, N, ["Outside", "Dome"], y_rng)
    fdgs.extend(srcs)
    res = make_plot(logger, dims, srcs, y_rng,
                    y_acc=np.mean, title="Humidity (%)",
                    warn_y=70, alert_y=80)
    vbox.add_widget(res.widget, stretch=1)
    plots.append(res)

    # make a plot of outside and dome dew point
    y_rng = (-30.0, 50.0)
    srcs = make_data(t, N, ["Outside", "Dome"], y_rng)
    fdgs.extend(srcs)
    res = make_plot(logger, dims, srcs, y_rng,
                    y_acc=np.mean, title="M1 & Dew (C)")
    vbox.add_widget(res.widget, stretch=1)
    plots.append(res)

    # make a plot of front and rear top-ring wind speed
    y_rng = (0.0, 50.0)
    srcs = make_data(t, N, ["Front", "Rear"], y_rng)
    fdgs.extend(srcs)
    res = make_plot(logger, dims, srcs, y_rng,
                    y_acc=np.mean, title="Top Ring Wind (m/s)")
    vbox.add_widget(res.widget, stretch=1)
    plots.append(res)

    # cross connect plots so zooming/panning in X affects all plots
    cross_connect_plots(plots)

    hbox = Widgets.HBox()
    hbox.set_margins(4, 2, 4, 2)

    wquit = Widgets.Button("Quit")
    wquit.add_callback('activated', quit)

    hbox.add_widget(Widgets.Label(''), stretch=1)
    hbox.add_widget(wquit)
    vbox.add_widget(hbox, stretch=0)

    w.set_widget(vbox)

    # timer to add a point every second
    t1 = app.make_timer()
    t1.add_callback('expired', timer1_cb, fdgs, 1.0)
    t1.set(1.0)

    # timer to update the plot every interval seconds
    t2 = app.make_timer()
    t2.add_callback('expired', timer2_cb, app, plots, fdgs,
                    options.update_interval)
    t2.set(options.update_interval)

    w.resize(win_wd, win_ht * len(plots) + 50)
    w.show()

    app.mainloop()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser("test ginga plot")

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("-n", "--numvalues", dest="numvalues", default=86400,
                        type=int,
                        help="Number of items to show per plot")
    argprs.add_argument("-m", "--numplots", dest="numplots", default=2,
                        type=int,
                        help="Number of plots to show per graph")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt)")
    argprs.add_argument("--update", dest="update_interval", default=5.0,
                        type=float,
                        help="Number of seconds between plot updates")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')

    else:
        main(options, args)
