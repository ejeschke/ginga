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

import gtk

class Debug(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Debug, self).__init__(fv)


    def build_gui(self, container):
        self.msgFont = self.fv.getFont("fixedFont", 14)
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_WORD)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.msgFont)
        self.tw = tw
        self.buf = self.tw.get_buffer()
        self.history = []
        self.histmax = 10
         
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)
        sw.add(self.tw)

        container.pack_start(sw, fill=True, expand=True)

        self.entry = gtk.Entry()
        container.pack_start(self.entry, fill=True, expand=False)
        self.entry.connect('activate', self.command_cb)


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
        self.buf.set_text('\n'.join(self.history))
        
    def command_cb(self, w):
        # TODO: implement a readline editing widget
        cmdstr = w.get_text().strip()
        self.command(cmdstr)
        w.set_text("")
        
    def __str__(self):
        return 'debug'
    
#END
