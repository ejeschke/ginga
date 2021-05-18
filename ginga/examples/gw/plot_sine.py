import sys

import numpy as np

import ginga.toolkit as ginga_toolkit
from ginga.misc import log

# window size
dims = (600, 440)


def main(options, args):
    logger = log.get_logger("sine", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    # now we can import
    from ginga.gw import Widgets, Viewers
    from ginga.canvas.types import plots as gplots
    from ginga.plot.plotaide import PlotAide

    app = Widgets.Application(logger=logger)

    def quit(*args):
        logger.info("Top window closed.")
        sys.exit()

    w = app.make_window("Sine")
    w.add_callback('close', quit)
    app.add_callback('shutdown', quit)

    vbox = Widgets.VBox()
    vbox.set_spacing(1)
    vbox.set_border_width(2)
    win_wd, win_ht = dims[:2]
    viewer = Viewers.CanvasView(logger, render='widget')
    viewer.set_desired_size(win_wd, win_ht)
    viewer.set_zoom_algorithm('rate')
    viewer.set_zoomrate(1.41)
    viewer.enable_autozoom('off')
    viewer.set_background('white')
    viewer.set_foreground('black')
    viewer.set_enter_focus(True)

    viewer.set_limits([(-2, -1), (2, 1)])

    # our plot assistant
    pa = PlotAide(viewer)
    pa.setup_standard_frame(title="Functions", x_title='x', y_title='f(x)')
    pa.settings['autoaxis_x'] = 'off'

    # add scrollbar interface around this viewer
    si = Viewers.GingaScrolledViewerWidget(viewer=viewer, width=win_wd,
                                           height=win_ht)
    pa.configure_scrollbars(si)

    vbox.add_widget(si, stretch=1)

    hbox = Widgets.HBox()
    btn = Widgets.Button("Quit")
    btn.add_callback('activated', quit)
    hbox.add_widget(Widgets.Label(''), stretch=1)
    hbox.add_widget(btn, stretch=0)
    vbox.add_widget(hbox, stretch=0)

    w.set_widget(vbox)

    plot = gplots.CalcPlot(name='Sin',
                           y_fn=np.sin, color='red', linewidth=2.0)
    pa.add_plot(plot)
    plot = gplots.CalcPlot(name='Cos',
                           y_fn=np.cos, color='blue', linewidth=2.0)
    pa.add_plot(plot)

    w.resize(win_wd, win_ht)
    w.show()
    w.raise_()

    pa.zoom_limit_x(-2.0, 2.0)
    pa.update_plots()

    try:
        app.mainloop()

    except KeyboardInterrupt:
        w.close()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt)")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    argprs.add_argument("-r", "--renderer", dest="renderer", metavar="NAME",
                        default=None,
                        help="Choose renderer (pil|agg|opencv|cairo|qt)")
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
