#! /usr/bin/env python3
"""
This example shows the use of the Ginga matplotlib-based plot viewer.
"""
import sys
from argparse import ArgumentParser

import numpy as np

import ginga.toolkit as ginga_toolkit
from ginga.misc import log
from ginga.plot.Plotable import Plotable

# window size
dims = (600, 440)


def main(options, args):
    logger = log.get_logger("sine", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    # now we can import
    from ginga.gw import Widgets
    from ginga.plot import PlotView

    app = Widgets.Application(logger=logger)

    def quit(*args):
        logger.info("Top window closed.")
        sys.exit()

    app.add_callback('shutdown', quit)
    if hasattr(Widgets, 'Page'):
        page = Widgets.Page("Plot sine2")
        app.add_window(page)
        top = Widgets.TopLevel("Plot sine2")
        page.add_dialog(top)
    else:
        top = Widgets.TopLevel("Plot sine2")
        app.add_window(top)
    top.add_callback('close', quit)

    vbox = Widgets.VBox()
    vbox.set_spacing(1)
    vbox.set_border_width(2)
    win_wd, win_ht = dims[:2]
    viewer = PlotView.CanvasView(logger=logger)
    viewer.set_enter_focus(True)

    bd = viewer.get_bindings()
    bd.enable_all(True)

    settings = viewer.get_settings()
    settings.set(plot_show_mode=True)

    viewer.set_limits([(-2, -1), (2, 1)])

    plot_w = viewer.get_ginga_widget()
    vbox.add_widget(plot_w, stretch=1)

    hbox = Widgets.HBox()
    btn = Widgets.Button("Quit")
    btn.add_callback('activated', quit)
    hbox.add_widget(Widgets.Label(''), stretch=1)
    hbox.add_widget(btn, stretch=0)
    vbox.add_widget(hbox, stretch=0)

    top.set_widget(vbox)

    x_data = np.arange(-3, 3.5, 0.01)
    y_sin = np.sin(x_data)
    y_cos = np.cos(x_data)

    plotable = Plotable(logger=logger)
    plotable.plot_line(np.array((x_data, y_sin)).T, color='red', tag='sin')
    plotable.plot_line(np.array((x_data, y_cos)).T, color='blue', tag='cos')
    plotable.set(title="Sin/Cos", x_axis_label="X", y_axis_label="Y",
                 grid=True)

    viewer.set_dataobj(plotable)
    # viewer.set_ranges(x_range=(-2.0, 3.5), y_range=(-1.0, 1.0))

    top.resize(win_wd, win_ht)
    top.show()
    top.raise_()

    try:
        app.mainloop()

    except KeyboardInterrupt:
        top.close()


if __name__ == "__main__":

    # Parse command line options
    argprs = ArgumentParser("Example of PlotView viewer")

    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt)")
    argprs.add_argument("-r", "--renderer", dest="renderer", metavar="NAME",
                        default=None,
                        help="Choose renderer (pil|agg|opencv|cairo|qt)")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    main(options, args)
