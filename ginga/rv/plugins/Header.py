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
from ginga.misc import Bunch
from ginga.gw import Widgets

__all__ = ['Header']


class Header(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Header, self).__init__(fv)

        self._image = None
        self.active = None
        self.info = None
        self.columns = [('Keyword', 'key'),
                        ('Value', 'value'),
                        ('Comment', 'comment'),
                        ]

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Header')
        self.settings.add_defaults(sortable=False,
                                   color_alternate_rows=True,
                                   max_rows_for_col_resize=5000,
                                   include_primary_header=False,
                                   closeable=not spec.get('hidden', False))
        self.settings.load(onError='silent')

        self.flg_sort = self.settings.get('sortable', False)
        self.flg_prihdr = self.settings.get('include_primary_header', False)
        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.add_callback('channel-change', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(1)
        vbox.set_spacing(1)

        nb = Widgets.StackWidget()
        vbox.add_widget(nb, stretch=1)
        self.nb = nb

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
            vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def _create_header_window(self, info):
        vbox = Widgets.VBox()
        vbox.set_margins(2, 2, 2, 2)

        color_alternate = self.settings.get('color_alternate_rows', True)
        table = Widgets.TreeView(auto_expand=True,
                                 use_alt_row_color=color_alternate)
        self.table = table
        table.setup_table(self.columns, 1, 'key')

        vbox.add_widget(table, stretch=1)

        info.setvals(widget=vbox, table=table)
        return vbox

    def set_header(self, info, image):
        if self._image == image:
            # we've already handled this header
            return
        self.logger.debug("setting header")

        if self.gui_up:
            has_prihdr = (hasattr(image, 'has_primary_header') and
                          image.has_primary_header())
            self.w.chk_prihdr.set_enabled(has_prihdr)

        header = image.get_header(include_primary_header=self.flg_prihdr)
        table = info.table

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

    def add_channel(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name
        info = Bunch.Bunch(chname=chname)
        sw = self._create_header_window(info)

        self.nb.add_widget(sw)
        info.setvals(widget=sw)
        channel.extdata._header_info = info

    def delete_channel(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        info = channel.extdata._header_info
        widget = info.widget
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None

    def focus_cb(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name

        if self.active != chname:
            if '_header_info' not in channel.extdata:
                self.add_channel(viewer, channel)
            info = channel.extdata._header_info
            widget = info.widget
            index = self.nb.index_of(widget)
            self.nb.set_index(index)
            self.active = chname
            self.info = info

        image = channel.get_current_image()
        if image is None:
            return
        self.set_header(self.info, image)

    def start(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.add_channel(self.fv, channel)

        channel = self.fv.get_channel_info()
        if channel is not None:
            viewer = channel.fitsimage

            image = viewer.get_image()
            if image is not None:
                self.redo(channel, image)

            self.focus_cb(viewer, channel)

    def stop(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            channel.extdata._header_info = None

        self.gui_up = False
        self.nb = None
        self.active = None
        self.info = None
        return True

    def redo(self, channel, image):
        """This is called when image changes."""
        self._image = None  # Skip cache checking in set_header()
        info = channel.extdata._header_info

        self.set_header(info, image)

    def blank(self, channel):
        """This is called when image is cleared."""
        self._image = None
        info = channel.extdata._header_info
        info.table.clear()

    def set_sortable_cb(self, tf):
        self.flg_sort = tf
        self._image = None
        if self.info is not None:
            info = self.info
            channel = self.fv.get_channel(info.chname)
            image = channel.get_current_image()
            self.set_header(info, image)

    def set_prihdr_cb(self, tf):
        self.flg_prihdr = tf
        self._image = None
        if self.info is not None:
            info = self.info
            channel = self.fv.get_channel(info.chname)
            image = channel.get_current_image()
            self.set_header(info, image)

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'header'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Header', package='ginga')

# END
