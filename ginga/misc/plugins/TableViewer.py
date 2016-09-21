#
# TableViewer.py -- Table viewer plugin for Ginga
#
from ginga.util.six.moves import zip

from collections import OrderedDict

from ginga.GingaPlugin import GlobalPlugin
from ginga.gw import Widgets
from ginga.misc import Bunch


class TableViewer(GlobalPlugin):
    """Plugin to display Astropy table."""
    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(TableViewer, self).__init__(fv)

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_TableViewer')
        self.settings.addDefaults(color_alternate_rows=True,
                                  max_rows_for_col_resize=5000)
        self.settings.load(onError='silent')

    def build_gui(self, container):
        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        # Create the Treeview
        color_alternate = self.settings.get('color_alternate_rows', True)
        self.treeview = Widgets.TreeView(auto_expand=True,
                                         sortable=True,
                                         use_alt_row_color=color_alternate)
        vbox.add_widget(self.treeview, stretch=1)

        container.add_widget(vbox, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        container.add_widget(btns, stretch=0)

        self.gui_up = True

    def display_table(self, tab, tabname='some table'):
        """Display the given Astropy table object."""
        if not self.gui_up:
            return

        self.clear()

        # Table header
        columns = [('Row', '_DISPLAY_ROW')] + [(c, c) for c in tab.colnames]
        self.treeview.setup_table(columns, 1, '_DISPLAY_ROW')

        # This is to get around table widget not sorting numbers properly
        i_fmt = '{{0:0{0}d}}'.format(len(str(len(tab))))

        tree_dict = OrderedDict()

        # Table contents
        for i, row in enumerate(tab, 1):
            bnch = Bunch.Bunch(zip(row.colnames, row.as_void()))
            bnch['_DISPLAY_ROW'] = i_fmt.format(i)
            tree_dict[i] = bnch

        self.treeview.set_tree(tree_dict)

        # Resize column widths
        n_rows = len(tree_dict)
        if n_rows < self.settings.get('max_rows_for_col_resize', 5000):
            self.treeview.set_optimal_column_widths()
            self.logger.debug('Resized columns for {0} row(s)'.format(n_rows))

        self.logger.debug('Displayed {0}'.format(tabname))

    def clear(self):
        self.treeview.clear()

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def stop(self):
        self.gui_up = False
        self.fv.showStatus('')

    def __str__(self):
        return 'tableviewer'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example  # noqa
__doc__ = generate_cfg_example('plugin_TableViewer', package='ginga')
