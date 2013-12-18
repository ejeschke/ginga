#
# Log.py -- Debugging plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import logging

from ginga import GingaPlugin

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

class Log(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Log, self).__init__(fv)

        self.histlimit = 1000
        self.histmax = 10000
        self.levels = (('Error', logging.ERROR),
                       ('Warn',  logging.WARN),
                       ('Info',  logging.INFO),
                       ('Debug', logging.DEBUG))

    def build_gui(self, container):
        #self.msgFont = self.fv.getFont("fixedFont", 10)
        tw = QtGui.QPlainTextEdit()
        tw.setReadOnly(True)
        #tw.setCurrentFont(self.msgFont)
        tw.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        tw.setMaximumBlockCount(self.histlimit)
        self.tw = tw
         
        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(True)
        sw.setWidget(self.tw)

        container.addWidget(sw, stretch=1)
        #sw.show()

        captions = (('Level', 'combobox', 'History', 'spinbutton'),
                    ('Auto scroll', 'checkbutton', 'Clear', 'button')
                    )
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        combobox = b.level
        for (name, level) in self.levels:
            combobox.addItem(name)
        combobox.setCurrentIndex(1)
        combobox.activated.connect(self.set_loglevel_cb)
        combobox.setToolTip("Set the logging level")
        
        spinbox = b.history
        spinbox.setRange(100, self.histmax)
        spinbox.setSingleStep(10)
        spinbox.setValue(self.histlimit)
        spinbox.valueChanged.connect(self.set_history_cb)
        spinbox.setToolTip("Set the logging history line limit")
        
        btn = b.auto_scroll
        btn.setToolTip("Scroll the log window automatically")

        btn = b.clear
        btn.clicked.connect(self.clear)
        btn.setToolTip("Clear the log history")
        container.addWidget(w, stretch=0)

    def set_history(self, histlimit):
        assert histlimit <= self.histmax, \
               Exception("Limit exceeds maximum value of %d" % (self.histmax))
        self.histlimit = histlimit
        self.logger.debug("Logging history limit set to %d" % (
            histlimit))
        self.tw.setMaximumBlockCount(self.histlimit)
        
    def set_history_cb(self, val):
        self.set_history(val)
        
    def set_loglevel_cb(self, index):
        name, level = self.levels[index]
        self.fv.set_loglevel(level)
        self.logger.info("GUI log level changed to '%s'" % (
            name))

    def log(self, text):
        try:
            self.tw.appendPlainText(text)
        except Exception as e:
            # widget may be destroyed
            return

        if not self.w.has_key('auto_scroll'):
            return
        scrollp = self.w.auto_scroll.isChecked()
        if scrollp:
            self.tw.moveCursor(QtGui.QTextCursor.End)
            self.tw.moveCursor(QtGui.QTextCursor.StartOfLine)
            self.tw.ensureCursorVisible()

    def clear(self):
        self.tw.clear()
        return True
        
    def __str__(self):
        return 'log'
    
#END
