#
# Debug.py -- Debugging plugin for Ginga
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw import Widgets
from ginga import GingaPlugin


class Debug(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Debug, self).__init__(fv)


    def build_gui(self, container):

        vbox = Widgets.VBox()

        self.msgFont = self.fv.getFont("fixedFont", 12)
        tw = Widgets.TextArea(wrap=False, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw
        self.history = []
        self.histmax = 10

        sw = Widgets.ScrollArea()
        sw.set_widget(self.tw)

        vbox.add_widget(sw, stretch=1)

        captions = (('Local plugin:', 'label', 'Local plugin', 'entry',
                     'Reload', 'button'),
                    ('Global plugin:', 'label', 'Global plugin', 'entry',
                     'ReloadG', 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.local_plugin.set_tooltip("Name of a local plugin to reload")
        b.local_plugin.set_length(14)
        b.reload.add_callback('activated', self.reload_local_cb)
        b.global_plugin.set_tooltip("Name of a global plugin to reload")
        b.global_plugin.set_length(14)
        b.reloadg.add_callback('activated', self.reload_global_cb)
        vbox.add_widget(w, stretch=1)

        self.entry = Widgets.TextEntry()
        vbox.add_widget(self.entry, stretch=0)
        self.entry.add_callback('activated', self.command_cb)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns)

        container.add_widget(vbox, stretch=1)


    def reloadLocalPlugin(self, plname):
        self.fv.mm.loadModule(plname)
        for chname in self.fv.get_channelNames():
            chinfo = self.fv.get_channelInfo(chname)
            chinfo.opmon.reloadPlugin(plname, chinfo=chinfo)
        return True

    def reload_local_cb(self, w):
        plname = self.w.local_plugin.get_text().strip()
        self.reloadLocalPlugin(plname)

    def reloadGlobalPlugin(self, plname):
        gpmon = self.fv.gpmon
        pInfo = gpmon.getPluginInfo(plname)
        gpmon.stop_plugin(pInfo)
        self.fv.update_pending(0.5)
        self.fv.mm.loadModule(plname)
        gpmon.reloadPlugin(plname)
        self.fv.start_global_plugin(plname)
        return True

    def reload_global_cb(self, w):
        plname = self.w.global_plugin.get_text().strip()
        self.reloadLocalPlugin(plname)

    def command(self, cmdstr):
        # Evaluate command
        try:
            result = eval(cmdstr)

        except Exception as e:
            result = str(e)
            # TODO: add traceback

        # Append command to history
        self.history.append('>>> ' + cmdstr + '\n' + str(result))

        # Remove all history past history size
        self.history = self.history[-self.histmax:]
        # Update text widget
        self.tw.set_text('\n'.join(self.history))

    def command_cb(self, w):
        # TODO: implement a readline editing widget
        cmdstr = str(w.get_text()).strip()
        self.command(cmdstr)
        w.set_text("")

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'debug'

#END
