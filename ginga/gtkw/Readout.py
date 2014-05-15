#
# Readout.py -- Readout for displaying image cursor information
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import gtk
from ginga.misc import Bunch

class Readout(object):

    def __init__(self, width, height):
        readout = gtk.Label('')
        #readout.set_size_request(width, height)
        readout.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("palegreen"))
        self.readout = readout
        evbox = gtk.EventBox()
        evbox.set_border_width(0)
        evbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#202030"))
        evbox.add(readout)
        evbox.show_all()
        self.evbox = evbox

        self.maxx = 0
        self.maxy = 0
        self.maxv = 0

        self.fitsimage = None

    def get_widget(self):
        return self.evbox

    def set_font(self, font):
        self.readout.modify_font(font)

    def set_text(self, text):
        self.readout.set_text(text)

        
# END
