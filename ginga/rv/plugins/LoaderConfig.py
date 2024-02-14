# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``LoaderConfig`` plugin allows you to configure the file openers that
can be used to load various content into Ginga.

Registered file openers are associated with file MIME types, and there can
be several openers for a single MIME type.  A priority associated
with a MIME type/opener pairing determines which opener will be used
for each type--the lowest priority value will determine which opener will
be used.  If there are more than one opener with the same low priority
then the user will be prompted for which opener to use, when opening a
file in Ginga.  This plugin can be used to set the opener preferences
and save it to the user's $HOME/.ginga configuration area.

**Plugin Type: Global**

``LoaderConfig`` is a global plugin.  Only one instance can be opened.

**Usage**

After starting the plugin, the display will show all the registered MIME
types and the openers registered for those types, with an associated
priority for each MIME type/opener pairing.

Select one or more lines and type a priority for them in the box labeled
"Priority:"; press "Set" (or ENTER) to set the priority of those items.

.. note:: The lower the number, the higher the priority. Negative numbers
          are fine and the default priority for a loader is usually 0.
          So, for example, if there are two loaders available for a MIME
          type and one priority is set to -1 and the other to 0, the one
          with -1 will be used without asking the user to choose.


Click "Save" to save the priorities to $HOME/.ginga/loaders.json so that
they will be reloaded and used on subsequent restarts of the program.
"""
import os.path

import yaml

from ginga import GingaPlugin
from ginga.util.paths import ginga_home
from ginga.util import loader
from ginga.gw import Widgets

__all__ = ['LoaderConfig']


class LoaderConfig(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        super().__init__(fv)

        self.loader_dct = dict()

        self.columns = [("Name", 'name'),
                        ("Priority", 'priority'),
                        ("Note", 'note')]

        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_spacing(1)

        tv = Widgets.TreeView(sortable=True, use_alt_row_color=True,
                              selection='multiple', auto_expand=True)
        tv.add_callback('selected', self.select_cb)
        tv.setup_table(self.columns, 2, 'name')
        self.w.loader_tbl = tv

        vbox.add_widget(tv, stretch=1)

        tbar = Widgets.HBox()
        tbar.set_border_width(4)
        tbar.set_spacing(4)

        tbar.add_widget(Widgets.Label('Priority:'))
        pri = Widgets.TextEntrySet(editable=True)
        pri.set_tooltip("Edit priority of loader (lower=better, negative numbers ok)")
        pri.set_enabled(False)
        pri.add_callback('activated', self.set_priority_cb)
        self.w.pri_edit = pri
        tbar.add_widget(pri)

        tbar.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(tbar, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Save")
        btn.add_callback('activated', lambda w: self.save_loaders_cb())
        btn.set_tooltip("Save configuration of loaders")
        btns.add_widget(btn, stretch=0)

        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)
        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def start(self):
        # create loader table
        tree_dct = dict()
        for mimetype, dct in loader.loader_by_mimetype.items():
            md = dict()
            tree_dct[mimetype] = md
            for name, bnch in dct.items():
                md[name] = dict(name=bnch.opener.name,
                                priority=bnch.priority,
                                note=bnch.opener.note)
            self.loader_dct = tree_dct

        self.w.loader_tbl.set_tree(self.loader_dct)
        self.w.loader_tbl.set_optimal_column_widths()

    def stop(self):
        self.gui_up = False

    def set_priority_cb(self, w):
        sel_dct = self.w.loader_tbl.get_selected()
        priority = int(self.w.pri_edit.get_text())
        for mimetype, ld_dct in sel_dct.items():
            for name, m_dct in ld_dct.items():
                self.loader_dct[mimetype][name]['priority'] = priority
                # actually change it in the loader registration
                opener = loader.get_opener(name)
                loader.add_opener(opener, [mimetype], priority=priority,
                                  note=opener.__doc__)
        # update the UI table
        self.w.loader_tbl.set_tree(self.loader_dct)

    def save_loaders_cb(self):
        path = os.path.join(ginga_home, 'loaders.yml')
        try:
            with open(path, 'w') as out_f:
                out_f.write(yaml.dump(self.loader_dct, indent=4))

        except Exception as e:
            self.logger.error(f"failed to save loader file: {e}",
                              exc_info=True)
            self.fv.show_error(str(e))

    def select_cb(self, w, dct):
        selected = len(dct) > 0
        self.w.pri_edit.set_enabled(selected)
        if not selected:
            self.w.pri_edit.set_text('')
        else:
            # only set priority widget if all selected are the same
            # unique value
            priorities = set([l_dct['priority']
                              for m_dct in dct.values()
                              for l_dct in m_dct.values()])
            if len(priorities) == 1:
                self.w.pri_edit.set_text(str(priorities.pop()))
            else:
                self.w.pri_edit.set_text('')

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'loaderconfig'
