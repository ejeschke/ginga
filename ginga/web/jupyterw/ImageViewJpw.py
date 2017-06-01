#
# ImageViewJpw.py -- Module for a Ginga FITS viewer in a Jupyter web notebook.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This example illustrates using a Ginga as the driver of a Jupyter web widget.

Basic usage in a Jupyter notebook:

from ipywidgets import *

# create a Jupyter image that will be our display surface
# format can be 'jpeg' or 'png'; specify width and height to set viewer size
jp_img = widgets.Image(format='jpeg', width=500, height=500)

# Boilerplate to create a Ginga viewer connected to this widget
# this could be simplified by creating a class that created viewers
# as a factory.
from ginga.misc.log import get_logger
logger = get_logger("v1", log_stderr=True, level=20)

from ginga.web.jupyterw.ImageViewJpw import EnhancedCanvasView
v1 = EnhancedCanvasView(logger=logger)
v1.set_widget(jp_img)

# You can now build a GUI with the image widget and other Jupyter
# widgets.  Here we just show the image widget.
v1.embed()

"""

# TODO: try for Agg backend first and fall back to PIL if not available
from ginga.pilw.ImageViewPil import CanvasView as CanvasViewPil
from ginga import AstroImage


class CanvasView(CanvasViewPil):

    def set_widget(self, jp_img):
        self.jp_img = jp_img

        # for some reason these are stored as strings!
        wd, ht = int(jp_img.width), int(jp_img.height)
        self.configure_surface(wd, ht)

    def get_widget(self):
        return self.jp_img

    def update_image(self):
        fmt = self.jp_img.format
        web_img = self.get_rgb_image_as_bytes(format=fmt)

        # this updates the model, and then the Jupyter image(s)
        self.jp_img.value = web_img


class EnhancedCanvasView(CanvasView):
    """
    This just adds some convenience methods to the viewer for loading images,
    grabbing screenshots, etc.  You can subclass to add new methods.
    """

    def embed(self):
        """
        Embed a viewer into a Jupyter notebook.
        """
        return self.jp_img

    def open(self, new=1):
        """
        Open this viewer in a new browser window or tab.
        """
        # TBD
        raise Exception("Not yet implemented!")

    def show(self, fmt=None):
        """
        Capture the window of a viewer.
        """
        # force any delayed redraws
        # TODO: this really needs to be addressed in get_rgb_image_as_bytes()
        # of the various superclasses, as it affects other backends as well
        self.redraw_now()

        from IPython.display import Image

        if fmt is None:
            # what format are we using for the Jupyter image--use that
            fmt = self.jp_img.format

        return Image(data=bytes(self.get_rgb_image_as_bytes(format=fmt)),
                     format=fmt, embed=True)

    def load_fits(self, filepath):
        """
        Load a FITS file into the viewer.
        """
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.set_image(image)

    load = load_fits

    def load_hdu(self, hdu):
        """
        Load an HDU into the viewer.
        """
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_hdu(hdu)

        self.set_image(image)

    def load_data(self, data_np):
        """
        Load raw numpy data into the viewer.
        """
        image = AstroImage.AstroImage(logger=self.logger)
        image.set_data(data_np)

        self.set_image(image)

    def add_canvas(self, tag=None):
        # add a canvas to the view
        my_canvas = self.get_canvas()
        DrawingCanvas = my_canvas.get_draw_class('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype(None)
        canvas.ui_set_active(True)
        canvas.set_surface(self)
        canvas.register_for_cursor_drawing(self)
        # add the canvas to the view.
        my_canvas.add(canvas, tag=tag)

        return canvas
