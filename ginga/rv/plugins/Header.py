# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Header`` plugin provides a listing of the metadata associated with the
image.

**Plugin Type: Global**

``Header`` is a global plugin.  Only one instance can be opened.

**Usage**

The ``Header`` plugin shows the FITS keyword metadata from the image.
Initially only the Primary HDU metadata is shown.  However, in
conjunction with the ``MultiDim`` plugin, the metadata for other HDUs will be
shown.  See ``MultiDim`` for details.

If the "Sortable" checkbox has been checked in the lower left of the UI,
then clicking on a column header will sort the table by values in that
column, which may be useful for quickly locating a particular keyword.

If the "Include primary header" checkbox toggles the inclusion of the
primary HDU keywords or not.  This option may be disabled if the image
was created with an option not to save the primary header.

"""
from collections import OrderedDict

from ginga import GingaPlugin
from ginga.gw import Widgets

__all__ = ['Header']


class Header(GingaPlugin.ParentPlugin):
    # Header uses the ParentPlugin class to share the same window amongst
    # a bunch of local plugins

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super().__init__(fv)

        # the child plugin class we will start for each channel opened
        self.class_childplugin = HeaderChild

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Header')
        self.settings.add_defaults(closeable=not spec.get('hidden', False))
        self.settings.load(onError='silent')

        self.gui_up = False

    def build_gui(self, container):
        super().build_gui(container)

        if self.settings.get('closeable', False):
            btns = Widgets.HBox()
            btns.set_border_width(4)
            btns.set_spacing(4)

            btn = Widgets.Button("Close")
            btn.add_callback('activated', lambda w: self.close())
            btns.add_widget(btn)
            btn = Widgets.Button("Help")
            btn.add_callback('activated', lambda w: self.help())
            btns.add_widget(btn, stretch=0)
            btns.add_widget(Widgets.Label(''), stretch=1)

            container.add_widget(btns, stretch=0)
        self.gui_up = True

    def __str__(self):
        return 'header'


class HeaderChild(GingaPlugin.ChildPlugin):
    # This local plugin actually does all the work, but only has to be
    # concerned with tracking a single channel

    def __init__(self, fv, image_viewer, parent_plugin):
        # superclass defines some variables for us, like logger
        super().__init__(fv, image_viewer, parent_plugin)

        self.columns = [('Keyword', 'key'),
                        ('Value', 'value'),
                        ('Comment', 'comment'),
                        ]

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Header')
        self.settings.add_defaults(sortable=False,
                                   color_alternate_rows=True,
                                   max_rows_for_col_resize=5000,
                                   include_primary_header=False)
        self.settings.load(onError='silent')

        self.flg_sort = self.settings.get('sortable', False)
        self.flg_prihdr = self.settings.get('include_primary_header', False)

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        color_alternate = self.settings.get('color_alternate_rows', True)
        table = Widgets.TreeView(auto_expand=True,
                                 use_alt_row_color=color_alternate)
        self.w.table = table
        table.setup_table(self.columns, 1, 'key')

        vbox.add_widget(table, stretch=1)

        # create sort toggle
        hbox = Widgets.HBox()
        cb = Widgets.CheckBox("Sortable")
        cb.set_state(self.flg_sort)
        cb.add_callback('activated', lambda w, tf: self.set_sortable_cb(tf))
        hbox.add_widget(cb, stretch=0)
        cb = Widgets.CheckBox("Include primary header")
        cb.set_state(self.flg_prihdr)
        cb.add_callback('activated', lambda w, tf: self.set_prihdr_cb(tf))
        self.w.chk_prihdr = cb
        hbox.add_widget(cb, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def set_header(self, image):
        if self._image == image:
            # we've already handled this header
            return
        self.logger.debug("setting header")

        if self.gui_up:
            has_prihdr = (hasattr(image, 'has_primary_header') and
                          image.has_primary_header())
            self.w.chk_prihdr.set_enabled(has_prihdr)

        header = image.get_header(include_primary_header=self.flg_prihdr)
        table = self.w.table

        is_sorted = self.flg_sort
        tree_dict = OrderedDict()

        keys = list(header.keys())
        if is_sorted:
            keys.sort()
        for key in keys:
            card = header.get_card(key)
            tree_dict[key] = card

        table.set_tree(tree_dict)

        # Resize column widths
        n_rows = len(tree_dict)
        if n_rows < self.settings.get('max_rows_for_col_resize', 5000):
            table.set_optimal_column_widths()
            self.logger.debug("Resized columns for {0} row(s)".format(n_rows))

        self.logger.debug("setting header done ({0})".format(is_sorted))
        self._image = image

    def start(self):
        pass

    def stop(self):
        self.gui_up = False

    def close(self):
        #self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def redo(self):
        """This is called when image changes."""
        self._image = None  # Skip cache checking in set_header()

        # TODO: what about tables and the table viewer?
        image = self.fitsimage.get_image()
        if image is None:
            self.w.table.clear()
        else:
            self.set_header(image)

    def set_sortable_cb(self, tf):
        self.flg_sort = tf
        self.redo()

    def set_prihdr_cb(self, tf):
        self.flg_prihdr = tf
        self.redo()

    def __str__(self):
        return 'headerchild'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Header', package='ginga')

# END
