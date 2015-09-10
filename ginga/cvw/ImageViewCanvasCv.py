#
# ImageViewCanvasCv.py -- A FITS image widget with canvas drawing in OpenCv
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.cvw import ImageViewCv
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin


class ImageViewCanvasError(ImageViewCv.ImageViewCvError):
    pass

class ImageViewCanvas(ImageViewCv.ImageViewCv,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindmap=None, bindings=None):
        ImageViewCv.ImageViewCv.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self)

        # we are both a viewer and a canvas
        self.set_canvas(self, private_canvas=self)

        # override
        self.defer_redraw = False

    # subclass needs to implement these to avoid warning messages
    def reschedule_redraw(self, time_sec):
        pass

    def update_image(self):
        pass

    # METHODS THAT WERE IN IPG

    def add_canvas(self, tag=None):
        # add a canvas to the view
        DrawingCanvas = self.getDrawClass('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.ui_setActive(True)
        canvas.setSurface(self)
        # add the canvas to the view.
        self.add(canvas, tag=tag)
        return canvas

    def show(self):
        from IPython.display import Image
        return Image(data=bytes(self.get_rgb_image_as_bytes(format='png')),
                     format='png', embed=True)

#END
