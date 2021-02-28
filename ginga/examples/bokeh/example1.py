"""

Usage:
  $ bokeh serve example1.py

you will see something like this in the output:
2017-11-29 17:00:48,368 Starting Bokeh server version 0.12.7 (running on Tornado 4.3)
2017-11-29 17:00:48,371 Bokeh app running at: http://localhost:5006/example1
2017-11-29 17:00:48,371 Starting Bokeh server with process id: 14214

Visit the URL with a browser to interact with the GUI.  Enter a valid
FITS file path into the box labeled "File:" and press Enter.
"""

import os
import tempfile
#import io, base64

from bokeh.layouts import column
from bokeh.plotting import figure, curdoc
from bokeh.models import TextInput, RadioButtonGroup, Div
#from bokeh.models.widgets import FileInput

from ginga.web.bokehw.ImageViewBokeh import CanvasView
from ginga.misc import log
from ginga import AstroImage
from ginga.util.loader import load_data


def main():

    # "bokeh serve" chokes on --log
    log_file = os.path.join(tempfile.gettempdir(), "example1.log")
    logger = log.get_logger("ginga", level=20, log_file=log_file)

    # viewer size
    wd, ht = 600, 600
    TOOLS = ""

    # create a new plot with default tools, using figure
    fig = figure(x_range=[0, wd], y_range=[0, ht],
                 plot_width=wd, plot_height=ht,
                 toolbar_location="below", toolbar_sticky=False,
                 tools=TOOLS, output_backend="webgl")
    viewer = CanvasView(logger=logger)
    viewer.set_figure(fig)
    viewer.enable_autocuts('on')
    viewer.set_color_map('rainbow3')
    viewer.set_autocut_params('zscale')
    viewer.enable_autozoom('on')
    viewer.set_zoom_algorithm('rate')
    viewer.set_zoomrate(1.4)
    viewer.show_pan_mark(True)
    viewer.show_mode_indicator(True)

    bd = viewer.get_bindings()
    bd.enable_all(True)
    bd.set_mode(viewer, 'pan', mode_type='locked')

    def load_file(path):
        image = load_data(path, logger=logger)
        viewer.set_image(image)

    def load_file_cb(attr, old_val, new_val):
        try:
            img = AstroImage.AstroImage(logger=logger)
            img.load_file(new_val.strip())
            viewer.set_image(img)
        except Exception as e:
            logger.error("problem loading file: {}".format(e), exc_info=True)

    # def upload_file_cb(attr, old_val, new_val):
    #     try:
    #         buf_bytes = base64.b64decode(new_val)
    #         io_f = io.BytesIO(buf_bytes)
    #         img = AstroImage.AstroImage(logger=logger)
    #         with fits.open(io_f, 'readonly') as in_f:
    #             img.load_hdu(in_f[0])
    #         viewer.set_image(img)
    #     except Exception as e:
    #         logger.error("problem loading file: {}".format(e), exc_info=True)

    labels = ["Pan", "Rotate", "Contrast", "Dist", "Cuts", "Cmap"]

    def mode_change_cb(attr_name, old_val, new_val):
        mode = labels[new_val].lower()
        bd.set_mode(viewer, mode, mode_type='locked')

    readout = Div(text="")

    def cursor_cb(viewer, button, data_x, data_y):
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x + viewer.data_off),
                                    int(data_y + viewer.data_off))

        except Exception:
            value = None

        fits_x, fits_y = data_x + 1, data_y + 1

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = viewer.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        readout.text = text

    viewer.add_callback('cursor-changed', cursor_cb)

    mode = RadioButtonGroup(labels=labels, active=0)
    mode.on_change('active', mode_change_cb)

    # add a entry widget and configure with the call back
    path_w = TextInput(value=os.environ['HOME'], title="File:")
    path_w.on_change('value', load_file_cb)

    layout = column(fig, readout, mode, path_w)
    curdoc().add_root(layout)


main()
