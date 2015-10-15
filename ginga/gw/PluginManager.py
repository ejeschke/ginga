#
# PluginManager.py -- Simple class to manage plugins.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc.PluginManager import PluginManagerBase, PluginManagerError
from ginga.gw import Widgets

class PluginManager(PluginManagerBase):
    """
    This provides the GUI support methods for the PluginManager.
    See PluginManagerBase for the general logic of this class.

    TODO: merge in PluginManagerBase
    """

    def set_widget(self, hbox):
        # TEMP: workaround until specialized Desktop class is deprecated
        if not isinstance(hbox, Widgets.WidgetBase):
            _hbox = Widgets.HBox()
            _hbox.widget = hbox
            if hasattr(_hbox, 'layout'):
                _hbox.layout = hbox.layout()
            hbox = _hbox
        self.hbox = hbox

    def update_taskbar(self, localmode=True):
        ## with self.lock:
        if localmode:
            for child in self.hbox.get_children():
                #self.hbox.remove(child)
                child.hide()
        for name in self.active.keys():
            bnch = self.active[name]
            bnch.widget.show()

    def add_taskbar(self, bnch):
        lname = bnch.pInfo.name.lower()
        menu = Widgets.Menu()
        item = menu.add_name("Focus")
        item.add_callback('activated', lambda *args: self.set_focus(lname))
        item = menu.add_name("Unfocus")
        item.add_callback('activated', lambda *args: self.clear_focus(lname))
        item = menu.add_name("Stop")
        item.add_callback('activated', lambda *args: self.deactivate(lname))

        lblname = bnch.lblname
        lbl = Widgets.Label(lblname, halign='center', style='clickable',
                            menu=menu)
        lbl.set_tooltip("Right click for menu")
        self.hbox.add_widget(lbl, stretch=0)

        lbl.add_callback('activated', self.set_focus_cb, lname)

        bnch.setvals(widget=lbl, label=lbl, menu=menu)

    def set_focus_cb(self, widget, lname):
        self.set_focus(lname)

    def remove_taskbar(self, bnch):
        self.logger.debug("removing widget from taskbar")
        self.hbox.remove(bnch.widget)
        bnch.widget = None
        bnch.label = None

    def highlight_taskbar(self, bnch):
        self.logger.debug("highlighting widget")
        if bnch.label is not None:
            bnch.label.set_color(bg=self.focuscolor)

    def unhighlight_taskbar(self, bnch):
        self.logger.debug("unhighlighting widget")
        if bnch.label is not None:
            bnch.label.set_color(bg='grey')

    def finish_gui(self, pInfo, vbox):
        pass

    def dispose_gui(self, pInfo):
        self.logger.debug("disposing of gui")
        vbox = pInfo.widget
        pInfo.widget = None
        #vbox.delete()

#END
