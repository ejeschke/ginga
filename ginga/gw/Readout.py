#
# Readout.py -- Readout for displaying image cursor information
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw import Widgets, Viewers
from ginga.misc import log
from ginga import colors

class Readout(object):

    def __init__(self, width, height):
        logger = log.get_logger(null=True)

        # We just use a ginga widget to implement the readout
        readout = Viewers.CanvasView(logger=logger)
        readout.set_desired_size(width, height)
        bg = colors.lookup_color('#202030')
        readout.set_bg(*bg)

        self.viewer = readout
        self.readout = Widgets.wrap(readout.get_widget())
        self.readout.resize(width, height)

        canvas = readout.get_canvas()
        Text = canvas.get_draw_class('text')
        xoff, yoff = 4, 4
        self.text_obj = Text(xoff, height-yoff, text='',
                             color='lightgreen', fontsize=14,
                             coord='canvas')
        canvas.add(self.text_obj, redraw=False)

        self.maxx = 0
        self.maxy = 0
        self.maxv = 0

        self.fitsimage = None

    def get_widget(self):
        return self.readout

    def set_font(self, font):
        # TODO: font format should be compatible with that used in Widgets
        if ' ' in font:
            font, fontsize = font.split()
            fontsize = int(fontsize)
            self.text_obj.fontsize = fontsize
        self.text_obj.font = font
        self.viewer.redraw(whence=3)

    def set_text(self, text):
        self.text_obj.text = text
        self.viewer.redraw(whence=3)


# END
