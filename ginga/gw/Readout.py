#
# Readout.py -- Readout for displaying image cursor information
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw import Viewers
from ginga.misc import log
from ginga import colors


class Readout:

    def __init__(self, width, height):
        logger = log.get_logger(null=True)

        # We just use a ginga widget to implement the readout
        readout = Viewers.CanvasView(logger=logger)
        readout.name = 'readout'
        readout.set_desired_size(width, height)

        readout_w = Viewers.GingaViewerWidget(viewer=readout)
        readout_w.set_expanding(True, False)
        readout_w.set_min_size(None, height)
        readout_w.set_max_size(None, height)

        bg = colors.lookup_color('#202030')
        readout.set_bg(*bg)

        self.viewer = readout
        self.readout = readout_w

        canvas = readout.get_canvas()
        Text = canvas.get_draw_class('text')
        xoff, yoff = 4, 4
        self.text_obj = Text(xoff, height - yoff, text='',
                             color='lightgreen', fontsize=14,
                             coord='window')
        canvas.add(self.text_obj, redraw=False)

        # these are set and used by the Cursor plugin
        self.maxx = 0
        self.maxy = 0
        self.maxv = 0

        self.ext_viewer = None

    def get_widget(self):
        return self.readout

    def set_font(self, font, fontsize=None):
        self.text_obj.font = font
        if fontsize is not None:
            self.text_obj.fontsize = fontsize
        self.viewer.redraw(whence=3)

    def set_text(self, text):
        self.text_obj.text = text
        self.viewer.redraw(whence=3)


# END
