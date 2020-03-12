#
# sv.py -- Module for generating simple Ginga viewers
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This is a module for generating simple Ginga viewers.

Example program:

    from ginga import toolkit
    toolkit.use('qt5')

    from ginga.gw import sv

    vf = sv.ViewerFactory()
    v = vf.make_viewer(name="Test", width=500, height=500)

    v.load("some.fits")
    vf.mainloop()
"""

import os.path

from ginga import AstroImage
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log
from ginga.Bindings import ImageViewBindings
from ginga.misc.Settings import SettingGroup
from ginga.util.paths import ginga_home
from ginga.util import loader

from ginga.gw import Widgets, Viewers


class BasicCanvasView(Viewers.CanvasView):

    def build_gui(self, container):
        """
        This is responsible for building the viewer's UI.  It should
        place the UI in ``container``.  Override this to make a custom
        UI.
        """
        self.frame = Viewers.GingaScrolledViewerWidget(viewer=self)
        container.set_widget(self.frame)

    def load(self, filepath):
        """
        Load a file into the viewer.
        """
        image = loader.load_data(filepath, logger=self.logger)
        self.set_image(image)

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
        canvas.set_draw_mode(None)

        return canvas

    def scroll_bars(self, onoff):
        self.frame.scroll_bars(horizontal=onoff, vertical=onoff)


class EnhancedCanvasView(BasicCanvasView):
    """
    Like BasicCanvasView, but includes a readout widget for when the
    cursor is moved over the canvas to display the coordinates.
    """

    def build_gui(self, container):
        """
        This is responsible for building the viewer's UI.  It should
        place the UI in ``container``.
        """
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        self.frame = Viewers.GingaScrolledViewerWidget(viewer=self)
        vbox.add_widget(self.frame, stretch=1)

        # set up to capture cursor movement for reading out coordinates

        # coordinates reported in base 1 or 0?
        self.pixel_base = 1.0

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        self.set_callback('cursor-changed', self.motion_cb)

        container.set_widget(vbox)

    def motion_cb(self, viewer, button, data_x, data_y):

        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x + 0.5), int(data_y + 0.5))

        except Exception:
            value = None

        pb = self.pixel_base
        fits_x, fits_y = data_x + pb, data_y + pb

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
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def set_readout_text(self, text):
        self.readout.set_text(text)


class ViewerFactory(object):
    """
    This is a factory class that churns out viewers.

    The most important method of interest is :meth:`get_viewer`.
    """

    def __init__(self, logger=None, app=None):
        if app is not None and logger is None:
            logger = app.logger
        if logger is None:
            logger = log.NullLogger()
        self.logger = logger

        if app is None:
            app = Widgets.Application(logger=self.logger)
        self.app = app
        self.dc = get_canvas_types()

        self.count = 0

    def make_viewer(self, viewer_class=None, name=None,
                    width=500, height=500):
        if viewer_class is None:
            viewer_class = BasicCanvasView

        self.count += 1
        if name is None:
            name = 'Viewer {}'.format(self.count)

        # load binding preferences if available
        cfgfile = os.path.join(ginga_home, "sv_bindings.cfg")
        bindprefs = SettingGroup(name='bindings', logger=self.logger,
                                 preffile=cfgfile)
        bindprefs.load(onError='silent')

        bd = ImageViewBindings(self.logger, settings=bindprefs)

        fi = viewer_class(self.logger, bindings=bd)

        # set up some reasonable defaults--user can change these later
        # if desired
        fi.set_autocut_params('zscale')
        fi.enable_autocuts('on')
        fi.enable_autozoom('on')
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.sv_parent = self

        # enable most key/mouse operations
        bd = fi.get_bindings()
        bd.enable_all(True)

        # set up a non-private canvas for drawing
        canvas = self.dc.DrawingCanvas()
        canvas.set_surface(fi)
        # add canvas to view
        private_canvas = fi.get_canvas()
        private_canvas.add(canvas)
        canvas.ui_set_active(True)
        fi.set_canvas(canvas)

        fi.set_desired_size(width, height)

        # add little mode indicator that shows modal states in
        # the corner
        fi.show_mode_indicator(True)

        # Have the viewer build it's UI into the container
        window = self.app.make_window(name)
        window.add_callback('close', self.close)
        fi.build_gui(window)
        wd, ht = fi.get_desired_size()

        window.show()
        window.resize(wd, ht)

        return fi

    def close(self, w):
        self.app.quit()

    def quit(self):
        self.app.quit()

    def mainloop(self):
        self.app.mainloop()
