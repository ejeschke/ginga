#
# ImageViewAgg.py -- a backend for Ginga using the aggdraw library
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga import ImageView
from ginga.aggw.CanvasRenderAgg import CanvasRenderer


class ImageViewAgg(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.surface = None
        self.rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

    def get_surface(self):
        return self.surface

    def configure_surface(self, width, height):
        # tell renderer about our new size
        self.renderer.resize((width, height))

        # inform the base class about the actual window size
        self.configure(width, height)

    def get_image_as_array(self):
        # TO BE DEPRECATED: DO NOT USE
        return self.renderer.get_surface_as_array()

    def get_image_as_buffer(self, output=None):
        # TO BE DEPRECATED: DO NOT USE
        return self.renderer.get_surface_as_buffer()

    def get_rgb_image_as_buffer(self, output=None, format='png', quality=90):
        # TO BE DEPRECATED: DO NOT USE
        return self.renderer.get_surface_as_rgb_format_buffer(output=output,
                                                              format=format,
                                                              quality=quality)

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        # TO BE DEPRECATED: DO NOT USE
        return self.renderer.get_surface_as_rgb_format_bytes(format=format,
                                                             quality=quality)

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        # TO BE DEPRECATED: DO NOT USE
        return self.renderer.save_surface_as_rgb_format_file(filepath,
                                                             format=format,
                                                             quality=quality)

    def update_image(self):
        # subclass implements this method to actually update a widget
        # from the agg surface
        self.logger.warning("Subclass should override this method")
        return False

    def set_cursor(self, cursor):
        # subclass implements this method to actually set a defined
        # cursor on a widget
        self.logger.warning("Subclass should override this method")

    def reschedule_redraw(self, time_sec):
        # subclass implements this method to call delayed_redraw() after
        # time_sec
        self.delayed_redraw()


class CanvasView(ImageViewAgg):
    """This class is defined to provide a non-event handling invisible
    viewer.
    """

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        # NOTE: bindmap, bindings are ignored
        ImageViewAgg.__init__(self, logger=logger, settings=settings,
                              rgbmap=rgbmap)
        self.defer_redraw = False

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas

    def update_image(self):
        pass

    def configure_window(self, width, height):
        return super(CanvasView, self).configure_surface(width, height)

# END
