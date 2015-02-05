#
# ImageViewCanvasQt.py -- A FITS image widget with canvas drawing in Qt
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import ImageView, Mixins
from ginga.qtw import ImageViewQt
from ginga.qtw.ImageViewCanvasTypesQt import *

class ImageViewCanvasError(ImageViewQt.ImageViewQtError):
    pass

class ImageViewCanvas(ImageViewQt.ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, settings=None, render=None,
                 rgbmap=None, bindmap=None, bindings=None):
        ImageViewQt.ImageViewZoom.__init__(self, logger=logger,
                                           settings=settings,
                                           render=render,
                                           rgbmap=rgbmap,
                                           bindmap=bindmap,
                                           bindings=bindings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)

        self.setSurface(self)
        self.ui_setActive(True)

        # for displaying modal keyboard state
        self.mode_obj = None
        bm = self.get_bindmap()
        bm.add_callback('mode-set', self.mode_change_cb)
        self.add_callback('configure', self._configure_cb)


    def canvascoords(self, data_x, data_y, center=True):
        # data->canvas space coordinate conversion
        x, y = self.get_canvas_xy(data_x, data_y, center=center)
        return (x, y)

    def redraw_data(self, whence=0):
        super(ImageViewCanvas, self).redraw_data(whence=whence)

        if not self.pixmap:
            return
        self.draw()

    def mode_change_cb(self, bindmap, mode, modetype):
        # delete the old indicator
        obj = self.mode_obj
        self.mode_obj = None
        if obj:
            try:
                self.deleteObject(obj)
            except:
                pass

        # if not one of the standard modifiers, display the new one
        if not mode in (None, 'ctrl', 'shift'):
            Text = self.getDrawClass('text')
            Rect = self.getDrawClass('rectangle')
            Compound = self.getDrawClass('compoundobject')

            if modetype == 'locked':
                text = '%s [L]' % (mode)
            else:
                text = mode
                
            xsp, ysp = 4, 6
            wd, ht = self.get_window_size()
            x1, y1 = wd-12*len(text), ht-12
            o1 = Text(x1, y1, text,
                      fontsize=12, color='yellow', coord='canvas')
            # hack necessary to be able to compute text extents _before_
            # adding the object to the canvas
            o1.viewer = self
            wd, ht = o1.get_dimensions()

            # yellow text on a black filled rectangle
            o2 = Compound(Rect(x1-xsp, y1+ysp, x1+wd+xsp, y1-ht,
                               color='black', coord='canvas',
                               fill=True, fillcolor='black'),
                               o1)
            # use canvas, not data coordinates
            self.mode_obj = o2
            self.add(o2)
            
        return True

    def _configure_cb(self, view, width, height):
        # redraw the mode indicator since the window has been resized
        bm = view.get_bindmap()
        mode, modetype = bm.current_modifier()
        self.mode_change_cb(bm, mode, modetype)
        
#END
