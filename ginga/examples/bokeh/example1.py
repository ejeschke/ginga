from __future__ import print_function

import sys, os
from bokeh.plotting import figure, curdoc, vplot
from bokeh.client import push_session
from bokeh.models.widgets import TextInput
from bokeh.models import BoxSelectTool, TapTool

from ginga.web.bokehw import ImageViewBokeh as ib
from ginga.misc import log
from ginga.AstroImage import AstroImage

def main(options, args):
    
    logger = log.get_logger("ginga", options=options)

    TOOLS = "pan,wheel_zoom,box_select,tap"
    
    # create a new plot with default tools, using figure
    fig = figure(x_range=[0,600], y_range=[0,600], plot_width=600, plot_height=600,
                 tools=TOOLS)

    viewer = ib.CanvasView(logger)
    viewer.set_figure(fig)

    ## box_select_tool = fig.select(dict(type=BoxSelectTool))
    ## box_select_tool.select_every_mousemove = True
    #tap_tool = fig.select_one(TapTool).renderers = [cr]

    # open a session to keep our local document in sync with server
    session = push_session(curdoc())

    #curdoc().add_periodic_callback(update, 50)

    def load_file(path):
        image = AstroImage(logger)
        image.load_file(path)
        viewer.set_image(image)

    def load_file_cb(attr_name, old_val, new_val):
        #print(attr_name, old_val, new_val)
        load_file(new_val)

    # add a entry widget and configure with the call back
    dstdir = options.indir
    path_w = TextInput(value=dstdir, title="File:")
    path_w.on_change('value', load_file_cb)

    curdoc().add_root(vplot(fig, path_w))

    if len(args) > 0:
        load_file(args[0])

    # open the document in a browser
    session.show() 

    # run forever
    session.loop_until_closed() 

if __name__ == "__main__":

    # Parse command line options 
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("-d", "--indir", dest="indir", metavar="DIR",
                      default=os.environ['HOME'],
                      help="Look in DIR for files")
    optprs.add_option("--opencv", dest="use_opencv", default=False,
                      action="store_true",
                      help="Use OpenCv acceleration")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")
    log.addlogopts(optprs)

    (options, args) = optprs.parse_args(sys.argv[1:])

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

# END
