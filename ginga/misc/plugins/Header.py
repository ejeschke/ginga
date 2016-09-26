#
# Header.py -- Image header plugin for Ginga viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from collections import OrderedDict

from ginga import GingaPlugin
from ginga.misc import Bunch
from ginga.gw import Widgets


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

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Header')
        self.settings.addDefaults(sortable=False,
                                  color_alternate_rows=True,
                                  max_rows_for_col_resize=5000)
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.add_callback('channel-change', self.focus_cb)

    def build_gui(self, container):
        nb = Widgets.StackWidget()
        self.nb = nb
        container.add_widget(nb, stretch=1)

    def _create_header_window(self, info):
        vbox = Widgets.VBox()
        vbox.set_margins(2, 2, 2, 2)

        color_alternate = self.settings.get('color_alternate_rows', True)
        table = Widgets.TreeView(auto_expand=True,
                                 use_alt_row_color=color_alternate)
        self.table = table
        table.setup_table(self.columns, 1, 'key')

        vbox.add_widget(table, stretch=1)

        # create sort toggle
        cb = Widgets.CheckBox("Sortable")
        cb.add_callback('activated', lambda w, tf: self.set_sortable_cb(info))
        hbox = Widgets.HBox()
        hbox.add_widget(cb, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        # toggle sort
        if self.settings.get('sortable', False):
            cb.set_state(True)

        info.setvals(widget=vbox, table=table, sortw=cb)
        return vbox

    def set_header(self, info, image):
        if self._image == image:
            # we've already handled this header
            return
        self.logger.debug("setting header")
        header = image.get_header()
        table = info.table

        is_sorted = info.sortw.get_state()
        tree_dict = OrderedDict()

        keys = list(header.keys())
        if is_sorted:
            keys.sort()
        for key in keys:
            card = header.get_card(key)
            # tree_dict[key] = Bunch.Bunch(key=card.key,
            #                              value=str(card.value),
            #                              comment=card.comment,
            #                              __terminal__=True)
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
        chname = channel.name
        info = Bunch.Bunch(chname=chname)
        sw = self._create_header_window(info)

        self.nb.add_widget(sw)
        # index = self.nb.index_of(sw)
        info.setvals(widget=sw)
        channel.extdata._header_info = info

    def delete_channel(self, viewer, channel):
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        info = channel.extdata._header_info
        widget = info.widget
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None

    def focus_cb(self, viewer, channel):
        chname = channel.name

        if self.active != chname:
            if not channel.extdata.has_key('_header_info'):
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

    def redo(self, channel, image):
        """This is called when buffer is modified."""
        self._image = None  # Skip cache checking in set_header()
        chname = channel.name
        info = channel.extdata._header_info

        self.set_header(info, image)

    def set_sortable_cb(self, info):
        self._image = None
        channel = self.fv.get_channel(info.chname)
        image = channel.get_current_image()
        self.set_header(info, image)

    def __str__(self):
        return 'header'

# END
