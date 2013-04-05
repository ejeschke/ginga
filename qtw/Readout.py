#
# Readout.py -- Readout for displaying image cursor information
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from QtHelp import QtGui, QtCore
import Bunch

class Readout(object):

    def __init__(self, width, height):
        readout = QtGui.QLabel('')
        readout.resize(width, height)
        readout.setStyleSheet("QLabel { background-color: #202030; color: lightgreen; }");
        readout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        self.readout = readout

        self.maxx = 0
        self.maxy = 0
        self.maxv = 0

    def get_widget(self):
        #return self.evbox
        return self.readout

    def set_font(self, font):
        self.readout.setFont(font)

    def set_text(self, text):
        self.readout.setText(text)

        
# END
