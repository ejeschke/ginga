#
# Operations.py -- Operations management plugin for Ginga viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Bunch
from ginga.gw import Widgets


class Operations(GingaPlugin.GlobalPlugin):
    """
    This plugin defines the GUI for managing local plugins, AKA "operations".
    By replacing or subclassing this plugin you can customize the way
    the reference viewer starts and manages operations.
    """

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Operations, self).__init__(fv)

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Operations')
        self.settings.addDefaults(show_channel_control=True,
                                  use_popup_menu=True,
                                  focuscolor="lightgreen")
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.change_channel_cb)
        fv.add_callback('add-operation', self.add_operation_cb)

        self.operations = list(fv.get_operations())

        self.focuscolor = self.settings.get('focuscolor', "lightgreen")
        self.use_popup = True

    def build_gui(self, container):

        hbox = Widgets.HBox()
        hbox.set_border_width(0)
        hbox.set_spacing(2)

        cbox1 = Widgets.ComboBox()
        self.w.channel = cbox1
        cbox1.set_tooltip("Select a channel")
        cbox1.add_callback('activated', self.channel_select_cb)
        if self.settings.get('show_channel_control', True):
            hbox.add_widget(cbox1, stretch=0)

        self.use_popup = self.settings.get('use_popup_menu', True)
        if self.use_popup:
            opmenu = Widgets.Menu()
            btn = Widgets.Button("Operation")
        else:
            opmenu = Widgets.ComboBox()
            opmenu.set_tooltip("Select an operation")
            hbox.add_widget(opmenu, stretch=0)
            btn = Widgets.Button("Go")

        self.w.operation = opmenu
        btn.add_callback('activated', self.invoke_op_cb)
        btn.set_tooltip("Invoke operation")
        self.w.opbtn = btn
        hbox.add_widget(btn, stretch=0)

        self.w.optray = Widgets.HBox()
        self.w.optray.set_border_width(0)
        self.w.optray.set_spacing(2)
        hbox.add_widget(self.w.optray, stretch=1)

        container.add_widget(hbox, stretch=0)


    def add_channel_cb(self, viewer, channel):
        chname = channel.name
        self.w.channel.insert_alpha(chname)

        pl_mgr = channel.opmon
        pl_mgr.add_callback('activate-plugin', self.activate_plugin_cb)
        pl_mgr.add_callback('deactivate-plugin', self.deactivate_plugin_cb)
        pl_mgr.add_callback('focus-plugin', self.focus_plugin_cb)
        pl_mgr.add_callback('unfocus-plugin', self.unfocus_plugin_cb)

        self.logger.debug("added channel %s" % (chname))

    def delete_channel_cb(self, viewer, channel):
        chname = channel.name
        self.w.channel.delete_alpha(chname)
        self.logger.debug("deleted channel %s" % (chname))

    def start(self):
        # get the list of channels and populate our channel control
        names = self.fv.get_channelNames()
        for name in names:
            channel = self.fv.get_channelInfo(name)
            self.add_channel_cb(self.fv, channel)

        # get the list of local plugins and populate our operation control
        operations = self.fv.get_operations()
        for opname in operations:
            self.add_operation_cb(self.fv, opname)

    def add_operation_cb(self, viewer, opname):
        opmenu = self.w.operation
        if self.use_popup:
            item = opmenu.add_name(opname)
            item.add_callback('activated',
                              lambda *args: self.start_operation_cb(opname))
        else:
            opmenu.insert_alpha(opname)

    def start_operation_cb(self, name):
        self.logger.debug("invoking operation menu")
        idx = self.w.channel.get_index()
        chname = str(self.w.channel.get_alpha(idx))
        self.fv.error_wrap(self.fv.start_local_plugin, chname, name, None)

    def channel_select_cb(self, widget, index):
        if index >= 0:
            chname = self.fv.get_channelNames()[index]
            self.logger.debug("Channel changed, index=%d chname=%s" % (
                index, chname))
            self.fv.change_channel(chname)

    def change_channel_cb(self, viewer, channel):
        # Update the channel control
        self.w.channel.show_text(channel.name)

    def invoke_op_cb(self, btn_w):
        self.logger.debug("invoking operation menu")
        menu = self.w.operation
        if self.use_popup:
            menu.popup(btn_w)
        else:
            idx = menu.get_index()
            opname = str(menu.get_alpha(idx))
            self.start_operation_cb(opname)

    def activate_plugin_cb(self, pl_mgr, bnch):
        lname = bnch.pInfo.name.lower()
        menu = Widgets.Menu()
        item = menu.add_name("Focus")
        item.add_callback('activated', lambda *args: pl_mgr.set_focus(lname))
        item = menu.add_name("Unfocus")
        item.add_callback('activated', lambda *args: pl_mgr.clear_focus(lname))
        item = menu.add_name("Stop")
        item.add_callback('activated', lambda *args: pl_mgr.deactivate(lname))

        lblname = bnch.lblname
        lbl = Widgets.Label(lblname, halign='center', style='clickable',
                            menu=menu)
        lbl.set_tooltip("Right click for menu")
        self.w.optray.add_widget(lbl, stretch=0)

        lbl.add_callback('activated', lambda w: pl_mgr.set_focus(lname))

        bnch.setvals(widget=lbl, label=lbl, menu=menu)

    def deactivate_plugin_cb(self, pl_mgr, bnch):
        if bnch.widget is not None:
            self.logger.debug("removing widget from taskbar")
            self.w.optray.remove(bnch.widget)
            bnch.widget = None
        bnch.label = None

    def focus_plugin_cb(self, pl_mgr, bnch):
        self.logger.debug("highlighting widget")
        if bnch.label is not None:
            bnch.label.set_color(bg=self.focuscolor)

    def unfocus_plugin_cb(self, pl_mgr, bnch):
        self.logger.debug("unhighlighting widget")
        if bnch.label is not None:
            bnch.label.set_color(bg='grey')

    def __str__(self):
        return 'operations'

#END
