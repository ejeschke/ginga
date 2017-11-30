"""

Usage:
  $ bokeh serve example1.py

you will see something like this in the output:
2017-11-29 17:00:48,368 Starting Bokeh server version 0.12.7 (running on Tornado 4.3)
2017-11-29 17:00:48,371 Bokeh app running at: http://localhost:5006/example1
2017-11-29 17:00:48,371 Starting Bokeh server with process id: 14214

Visit the URL with a browser to interact with the GUI.  Enter a valid
FITS file path into the box labeled "File:" and press Enter.  Use the
slider to zoom the image.
"""
from __future__ import print_function

import sys

from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.plotting import figure
#from bokeh.client import push_session
from bokeh.models import TextInput, Slider

from ginga.web.bokehw import ImageViewBokeh as ib
from ginga.misc import log
from ginga.AstroImage import AstroImage


def main(options, args):

    #logger = log.get_logger("ginga", options=options)
    logger = log.get_logger("ginga", level=20, log_file="/tmp/ginga.log")

    #TOOLS = "pan,wheel_zoom,box_select,tap"
    TOOLS = "box_select"

    # create a new plot with default tools, using figure
    fig = figure(x_range=[0, 600], y_range=[0, 600],
                 plot_width=600, plot_height=600, tools=TOOLS)

    viewer = ib.CanvasView(logger)
    viewer.set_figure(fig)

    bd = viewer.get_bindings()
    bd.enable_all(True)

    ## box_select_tool = fig.select(dict(type=BoxSelectTool))
    ## box_select_tool.select_every_mousemove = True
    #tap_tool = fig.select_one(TapTool).renderers = [cr]

    # open a session to keep our local document in sync with server
    #session = push_session(curdoc())

    #curdoc().add_periodic_callback(update, 50)

    def load_file(path):
        image = AstroImage(logger=logger)
        image.load_file(path)
        viewer.set_image(image)

    def load_file_cb(attr_name, old_val, new_val):
        #print(attr_name, old_val, new_val)
        load_file(new_val)

    def zoom_ctl_cb(attr_name, old_val, new_val):
        if new_val >= 0:
            new_val += 2
        viewer.zoom_to(int(new_val))
        scale = viewer.get_scale()
        logger.info("%f" % scale)
        viewer.onscreen_message("%f" % (scale), delay=0.3)

    # add a entry widget and configure with the call back
    #dstdir = options.indir
    dstdir = ""
    path_w = TextInput(value=dstdir, title="File:")
    path_w.on_change('value', load_file_cb)

    slide = Slider(start=-20, end=20, step=1, value=1)
    slide.on_change('value', zoom_ctl_cb)

    layout = column(fig, path_w, slide)
    curdoc().add_root(layout)

    if len(args) > 0:
        load_file(args[0])

    # open the document in a browser
    #session.show()

    # run forever
    #session.loop_until_closed()


main(None, sys.argv[1:])

# END
