#
# Readout.py -- Readout for displaying image cursor information
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw import Widgets
from ginga.misc import Bunch

class Readout(object):

    def __init__(self, width, height):
        readout = Widgets.Label('', halign='center', style='clickable')
        #readout.resize(width, height)
        readout.set_color(bg="#202030", fg="lightgreen")

        self.readout = readout

        self.maxx = 0
        self.maxy = 0
        self.maxv = 0

        self.fitsimage = None

    def get_widget(self):
        return self.readout

    def set_font(self, font):
        self.readout.set_font(font)

    def set_text(self, text):
        self.readout.set_text(text)


# END
