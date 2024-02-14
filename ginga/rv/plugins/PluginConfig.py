# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``PluginConfig`` plugin allows you to configure the plugins that
are visible in your menus.

**Plugin Type: Global**

``PluginConfig`` is a global plugin.  Only one instance can be opened.

**Usage**

PluginConfig is used to configure plugins to be used in Ginga.  The items
that can be configured for each plugin include:

* whether it is enabled (and therefore whether it shows up in the menus)
* the category of the plugin (used to construct the menu hierarchy)
* the workspace in which the plugin will open
* if a global plugin, whether it starts automatically when the reference
  viewer starts
* Whether the plugin name should be hidden (not show up in plugin
  activation menus)

When PluginConfig starts, it will show a table of plugins.  To edit the
above attributes for plugins, click "Edit", which will bring up a dialog
for editing the table.

For each plugin you want to configure, click on an entry in the main table
and then adjust the settings in the dialog, then click "Set" in the dialog
to reflect the changes back into the table.  If you don't click "Set",
nothing is changed in the table.  When you are done editing configurations,
click "Close" on the dialog to close the editing dialog.

.. note:: It is not recommended to change the workspace for a plugin
          unless you choose a compatibly-sized workspace to the original,
          as the plugin may not display correctly.  If in doubt, leave
          the workspace unchanged.  Also, disabling plugins in the
          "Systems" category may cause some expected features to stop
          working.


.. important:: To make the changes persist across Ginga restarts, click
               "Save" to save the settings (to `$HOME/.ginga/plugins.json`).
               Restart Ginga to see changes to the menus (via "category"
               changes).  **Remove this file manually if you want to reset
               the plugin configurations to the defaults**.


"""
import os.path

import yaml

from ginga import GingaPlugin
from ginga.util.paths import ginga_home
from ginga.gw import Widgets

__all__ = ['PluginConfig']


class PluginConfig(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        super().__init__(fv)

        self.plugin_dct = dict()

        self.columns = [("Name", 'name'),
                        ("Enabled", 'enabled'),
                        ("Type", 'ptype'),
                        ("Category", 'category'),
                        ("Workspace", 'workspace'),
                        ("Hidden", 'hidden'),
                        ("Auto Start", 'start')]

        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_spacing(1)

        tv = Widgets.TreeView(sortable=True, use_alt_row_color=True,
                              selection='multiple')
        tv.add_callback('selected', self.select_cb)
        tv.setup_table(self.columns, 0, 'name')
        self.w.plugin_tbl = tv
        self.w.edit_dialog = None

        vbox.add_widget(tv, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Edit")
        btn.add_callback('activated', self.edit_plugin_selections_cb)
        btn.set_tooltip("Edit configuration of selected plugins")
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Save")
        btn.add_callback('activated', lambda w: self.save_plugins_cb())
        btn.set_tooltip("Save configuration of plugins\n"
                        "(restart Ginga to see changes to menus)")
        btns.add_widget(btn, stretch=0)

        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)
        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def start(self):
        if len(self.plugin_dct) == 0:
            # create plugin table if we haven't already done so
            dct = dict()
            for spec in self.fv.plugins:
                module = spec['module']
                klass = spec.get('klass', None)
                name = spec.get('name', module if klass is None else klass)
                enabled = spec.get('enabled', True)
                ptype = spec['ptype']
                start = 'False' if ptype == 'local' else str(spec.get('start', False))
                _dct = dict(name=name,
                            module=module,
                            enabled=str(enabled),
                            ptype=spec['ptype'],
                            category=spec.get('category', 'Custom'),
                            workspace=spec.get('workspace', 'in:dialog'),
                            hidden=str(spec.get('hidden', False)),
                            start=start)
                for key in ('menu', 'tab', 'klass'):
                    if key in spec:
                        _dct[key] = spec[key]
                dct[name] = _dct
            self.plugin_dct = dct

        self.w.plugin_tbl.set_tree(self.plugin_dct)
        self.w.plugin_tbl.set_optimal_column_widths()

    def stop(self):
        self.gui_up = False

    def edit_plugin_selections_cb(self, w):
        # build dialog for editing
        captions = (("Enabled", 'checkbox'),
                    ("Category:", 'label', "category", 'textentry'),
                    ("Workspace:", 'label', "workspace", 'textentry'),
                    ("Auto start", 'checkbox', "Hidden", 'checkbox'),
                    )

        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        b.enabled.set_tooltip("Enable plugin(s)")
        b.enabled.set_enabled(False)
        b.category.set_tooltip("Edit menu category of plugin(s)")
        b.category.set_enabled(False)
        b.workspace.set_tooltip("Edit workspace of plugin(s)")
        b.workspace.set_enabled(False)
        b.auto_start.set_tooltip("Start plugin(s) at program startup\n"
                                 "(for global plugins only)")
        b.auto_start.set_enabled(False)
        b.hidden.set_tooltip("Hide plugin(s) names from program menus")
        b.hidden.set_enabled(False)

        dialog = Widgets.Dialog(title="Edit Plugin Configuration",
                                flags=0,
                                modal=False,
                                buttons=[['Set', 0], ['Close', 1]],
                                parent=self.w.plugin_tbl)
        dialog.add_callback('activated',
                            lambda w, rsp: self.edit_cb(w, rsp))
        self.w.edit_dialog = dialog

        box = dialog.get_content_area()
        box.set_border_width(4)
        box.add_widget(w, stretch=0)

        sel_dct = self.w.plugin_tbl.get_selected()
        self.select_cb(self.w.plugin_tbl, sel_dct)

        self.fv.ds.show_dialog(self.w.edit_dialog)

    def edit_cb(self, w, rsp):
        if rsp == 1:
            # close
            self.fv.ds.remove_dialog(w)
            self.w.edit_dialog = None
            return

        sel_dct = self.w.plugin_tbl.get_selected()
        if len(sel_dct) == 0:
            self.fv.show_error("No table entries selected",
                               raisetab=True)
            return

        enabled = self.w.enabled.get_state()
        category = self.w.category.get_text().strip()
        workspace = self.w.workspace.get_text().strip()
        hidden = self.w.hidden.get_state()
        start = self.w.auto_start.get_state()

        if len(category) == 0:
            self.fv.show_error("Category field should not be empty",
                               raisetab=True)
            return

        if len(workspace) == 0:
            self.fv.show_error("Workspace field should not be empty",
                               raisetab=True)
            return

        for name, pl_dct in sel_dct.items():
            self.plugin_dct[name]['enabled'] = str(enabled)
            self.plugin_dct[name]['category'] = category
            self.plugin_dct[name]['workspace'] = workspace
            if self.plugin_dct[name]['ptype'] == 'global':
                self.plugin_dct[name]['start'] = str(start)
            self.plugin_dct[name]['hidden'] = str(hidden)

        self.w.plugin_tbl.set_tree(self.plugin_dct)

    def save_plugins_cb(self):
        path = os.path.join(ginga_home, 'plugins.yml')
        _plugins = []
        for key, dct in self.plugin_dct.items():
            d = dct.copy()
            d['enabled'] = (d['enabled'] == 'True')
            if d['ptype'] == 'global':
                d['start'] = (d['start'] == 'True')
            else:
                d['start'] = False
            d['hidden'] = (d['hidden'] == 'True')
            _plugins.append(d)
        try:
            with open(path, 'w') as out_f:
                out_f.write(yaml.dump(_plugins))

        except Exception as e:
            self.logger.error(f"failed to save plugin file: {e}",
                              exc_info=True)
            self.fv.show_error(str(e))

    def select_cb(self, w, dct):
        if self.w.edit_dialog is None:
            return
        selected = len(dct) > 0
        self.w.enabled.set_enabled(selected)
        enabled = set([p_dct['enabled'] for p_dct in dct.values()])
        if len(enabled) == 1:
            self.w.enabled.set_state(enabled.pop() == 'True')
        else:
            self.w.enabled.set_state(True)

        self.w.category.set_enabled(selected)
        # only set category widget if all selected are the same
        # unique value
        categories = set([p_dct['category'] for p_dct in dct.values()])
        if len(categories) == 1:
            self.w.category.set_text(categories.pop())
        else:
            self.w.category.set_text('')

        self.w.workspace.set_enabled(selected)
        # only set workspace widget if all selected are the same
        # unique value
        workspaces = set([p_dct['workspace'] for p_dct in dct.values()])
        if len(workspaces) == 1:
            self.w.workspace.set_text(workspaces.pop())
        else:
            self.w.workspace.set_text('')

        # only enable auto start widget if all ptypes are 'global'
        ptypes = set([p_dct['ptype'] for p_dct in dct.values()])
        self.w.auto_start.set_enabled(len(ptypes) == 1 and 'global' in ptypes)

        starts = set([p_dct['start'] for p_dct in dct.values()])
        if len(starts) == 1:
            auto_start = (starts.pop() == 'True')
            self.w.auto_start.set_state(auto_start)
        else:
            self.w.auto_start.set_state(False)

        # only set hidden widget if all selected are hidden == 'True'
        self.w.hidden.set_enabled(selected)
        hiddens = set([p_dct['hidden'] for p_dct in dct.values()])
        if len(hiddens) == 1:
            hidden = (hiddens.pop() == 'True')
            self.w.hidden.set_state(hidden)
        else:
            self.w.hidden.set_state(False)

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'pluginconfig'
