#
# Debug.py -- Debugging plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin

from ginga.qtw.QtHelp import QtGui, QtCore

class Debug(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Debug, self).__init__(fv)


    def build_gui(self, container):
        rvbox = container

        self.msgFont = self.fv.getFont("fixedFont", 14)
        tw = QtGui.QTextEdit()
        #tw.setLineWrapMode(??)
        ## tw.set_left_margin(4)
        ## tw.set_right_margin(4)
        tw.setReadOnly(True)
        ## tw.set_left_margin(4)
        ## tw.set_right_margin(4)
        tw.setCurrentFont(self.msgFont)
        self.tw = tw
        self.history = []
        self.histmax = 10
         
        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(True)
        #sw.set_border_width(2)
        sw.setWidget(self.tw)

        rvbox.addWidget(sw, stretch=1)
        sw.show()

        self.entry = QtGui.QLineEdit()
        rvbox.addWidget(self.entry, stretch=0)
        self.entry.returnPressed.connect(self.command_cb)


    def reloadLocalPlugin(self, plname):
        self.fv.mm.loadModule(plname)
        for chname in self.fv.get_channelNames():
            chinfo = self.fv.get_channelInfo(chname)
            chinfo.opmon.reloadPlugin(plname, chinfo=chinfo)
        return True
            
    def reloadGlobalPlugin(self, plname):
        gpmon = self.fv.gpmon
        pInfo = gpmon.getPluginInfo(plname)
        gpmon.stop_plugin(pInfo)
        self.fv.update_pending(0.5)
        self.fv.mm.loadModule(plname)
        gpmon.reloadPlugin(plname)
        self.fv.start_global_plugin(plname)
        return True

    def command(self, cmdstr):
        # Evaluate command
        try:
            result = eval(cmdstr)

        except Exception, e:
            result = str(e)
            # TODO: add traceback

        # Append command to history
        self.history.append('>>> ' + cmdstr + '\n' + str(result))

        # Remove all history past history size
        self.history = self.history[-self.histmax:]
        # Update text widget
        self.tw.setText('\n'.join(self.history))
        
    def command_cb(self):
        w = self.entry
        # TODO: implement a readline editing widget
        cmdstr = str(w.text()).strip()
        self.command(cmdstr)
        w.setText("")
        
    def __str__(self):
        return 'debug'
    
#END
