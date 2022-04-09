# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
This plugin defines the GUI for managing local plugins, a.k.a., "operations".

**Plugin Type: Global**

``Operations`` is a global plugin.  Only one instance can be opened.

**Usage**

The ``Operations`` plugin acts as a visual interface to the reference viewer
plugin manager.  With this plugin, you can change the active channel,
start, stop, or unfocus a local plugin on a channel, and see which local
plugins are running.

.. note:: By replacing or subclassing this plugin, you can customize the way
          the reference viewer starts and manages operations.

"""
from ginga import GingaPlugin
from ginga.gw import Widgets

__all__ = ['Operations']


class Operations(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Operations, self).__init__(fv)

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Operations')
        self.settings.add_defaults(show_channel_control=True,
                                   use_popup_menu=True,
                                   focuscolor="lightgreen")
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.change_channel_cb)

        # Add in global plugin manager
        pl_mgr = self.fv.gpmon
        pl_mgr.add_callback('activate-plugin', self.activate_plugin_cb)
        pl_mgr.add_callback('deactivate-plugin', self.deactivate_plugin_cb)
        pl_mgr.add_callback('focus-plugin', self.focus_plugin_cb)
        pl_mgr.add_callback('unfocus-plugin', self.unfocus_plugin_cb)

        self.focuscolor = self.settings.get('focuscolor', "lightgreen")
        self.use_popup = True
        self._start_op_args = ()
        self.spacer = None
        self.gui_up = False

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
        opmenu = Widgets.Menu()
        btn = Widgets.Button("Operation")
        btn.set_tooltip("Invoke operation")
        btn.add_callback('activated', self.invoke_popup_cb)
        if not self.use_popup:
            hbox.add_widget(btn, stretch=0)
            self.w.opname = Widgets.Label('')
            hbox.add_widget(self.w.opname, stretch=0)
            btn = Widgets.Button("Go")
            btn.add_callback('activated', self.invoke_op_cb)

        self.w.operation = opmenu
        self.w.opbtn = btn
        hbox.add_widget(btn, stretch=0)

        self.w.optray = Widgets.HBox()
        self.w.optray.set_border_width(0)
        self.w.optray.set_spacing(2)

        # add a spacer to keep the icons aligned to the left
        self.spacer = Widgets.Label('')
        self.w.optray.add_widget(self.spacer, stretch=1)

        hbox.add_widget(self.w.optray, stretch=1)
        container.add_widget(hbox, stretch=0)
        self.gui_up = True

    def add_channel_cb(self, viewer, channel):
        if not self.gui_up:
            return
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
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.add_channel_cb(self.fv, channel)

        plugins = self.fv.get_plugins()
        for spec in plugins:
            if spec.get('hidden', False):
                continue
            self.fv.error_wrap(self.add_operation, self.fv, spec)

    def add_operation(self, viewer, spec):
        if not self.gui_up:
            return
        opname = spec.get('name', spec.get('klass', spec.get('module')))
        ptype = spec.get('ptype', 'local')
        category = spec.get('category', None)
        categories = None
        if category is not None:
            categories = category.split('.')
        menuname = spec.get('menu', spec.get('tab', opname))

        opmenu = self.w.operation
        menu = opmenu
        if categories is not None:
            for catname in categories:
                try:
                    menu = menu.get_menu(catname)
                except KeyError:
                    menu = menu.add_menu(catname)

        item = menu.add_name(menuname)
        if self.use_popup:
            item.add_callback('activated',
                              lambda *args: self.start_operation_cb(opname,
                                                                    ptype,
                                                                    spec))
        else:
            item.add_callback('activated',
                              lambda *args: self.set_operation_cb(menuname,
                                                                  opname,
                                                                  ptype,
                                                                  spec))

    def start_operation_cb(self, name, ptype, spec):
        if not self.gui_up:
            return
        self.logger.debug("invoking operation menu")
        if ptype == 'global':
            # global plugin
            self.fv.error_wrap(self.fv.start_global_plugin, name,
                               raise_tab=True)
            return

        idx = self.w.channel.get_index()
        chname = str(self.w.channel.get_alpha(idx))
        self.fv.error_wrap(self.fv.start_local_plugin, chname, name, None)

    def set_operation_cb(self, menuname, name, ptype, spec):
        self._start_op_args = (name, ptype, spec)
        self.w.opname.set_text(menuname)

    def channel_select_cb(self, widget, index):
        if index >= 0:
            chname = self.fv.get_channel_names()[index]
            self.logger.debug("Channel changed, index=%d chname=%s" % (
                index, chname))
            self.fv.change_channel(chname)

    def change_channel_cb(self, viewer, channel):
        # Update the channel control
        self.w.channel.show_text(channel.name)

    def invoke_popup_cb(self, btn_w):
        self.logger.debug("invoking operation menu")
        menu = self.w.operation
        menu.popup(btn_w)

    def invoke_op_cb(self, btn_w):
        args = self._start_op_args
        if len(args) == 0:
            return
        self.start_operation_cb(*args)

    def activate_plugin_cb(self, pl_mgr, bnch):
        if not self.gui_up:
            return
        spec = bnch.pInfo.spec
        optray = spec.get('optray', True)
        if not optray:
            return
        hidden = spec.get('hidden', False)
        if hidden:
            return

        lname = bnch.pInfo.name.lower()
        menu = Widgets.Menu()
        item = menu.add_name("Focus")
        item.add_callback('activated', lambda *args: pl_mgr.set_focus(lname))
        item = menu.add_name("Unfocus")
        item.add_callback('activated', lambda *args: pl_mgr.clear_focus(lname))
        item = menu.add_name("Stop")
        item.add_callback('activated', lambda *args: pl_mgr.deactivate(lname))
        item = menu.add_name("Reload")
        item.add_callback('activated',
                          lambda *args: pl_mgr.stop_reload_start(lname))

        lblname = bnch.lblname
        lbl = Widgets.Label(lblname, halign='center', style='clickable',
                            menu=menu)
        lbl.set_tooltip("Right click for menu")
        # don't let this widget expand to fill the bar
        lbl.cfg_expand(horizontal='fixed', vertical='expanding')
        self.w.optray.remove(self.spacer)
        self.w.optray.add_widget(lbl, stretch=0)
        self.w.optray.add_widget(self.spacer, stretch=1)

        bnch.setvals(widget=lbl, label=lbl, menu=menu)
        lbl.add_callback('activated', lambda w: pl_mgr.set_focus(lname))

    def deactivate_plugin_cb(self, pl_mgr, bnch):
        if not self.gui_up:
            return
        hidden = bnch.pInfo.spec.get('hidden', False)
        if hidden:
            return

        if bnch.widget is not None:
            self.logger.debug("removing widget from taskbar")
            self.w.optray.remove(bnch.widget)
            bnch.widget = None
        bnch.label = None

    def focus_plugin_cb(self, pl_mgr, bnch):
        if not self.gui_up:
            return
        self.logger.debug("highlighting widget")
        # plugin may not have been started by us, so don't assume it has
        # a label
        bnch.setdefault('label', None)
        if bnch.label is not None:
            bnch.label.set_color(bg=self.focuscolor)

    def unfocus_plugin_cb(self, pl_mgr, bnch):
        if not self.gui_up:
            return
        self.logger.debug("unhighlighting widget")
        # plugin may not have been started by us, so don't assume it has
        # a label
        bnch.setdefault('label', None)
        if bnch.label is not None:
            bnch.label.set_color(bg='grey')

    def stop(self):
        self.gui_up = False

    def __str__(self):
        return 'operations'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Operations', package='ginga')

# END
