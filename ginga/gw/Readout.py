#
# Readout.py -- Readout for displaying image cursor information
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw import Widgets


class Readout:

    def __init__(self, width, height):
        # We just use a Label widget to implement the readout
        readout_w = Widgets.Label('')
        readout_w.set_halign('left')
        readout_w.set_valign('center')
        readout_w.set_font('fixed', 14)
        readout_w.set_expanding(True, False)
        readout_w.set_min_size(None, height)
        readout_w.set_max_size(None, height)
        readout_w.set_color(fg='lightgreen', bg='#202030')
        self.readout = readout_w

        # these are set and used by the Cursor plugin
        self.maxx = 0
        self.maxy = 0
        self.maxv = 0

        self.ext_viewer = None

    def get_widget(self):
        return self.readout

    def set_font(self, font, fontsize=None):
        if fontsize is None:
            fontsize = 14
        self.readout.set_font(font, fontsize)

    def set_text(self, text):
        self.readout.set_text(" " + text)


# END
