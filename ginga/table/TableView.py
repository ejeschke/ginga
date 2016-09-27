#
# TableView.py -- Table viewer for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.util.six import itervalues
from ginga.util.six.moves import zip

import logging
from collections import OrderedDict

from ginga.table import AstroTable
from ginga.misc import Callback, Settings
from ginga.misc import Bunch


class TableViewBase(Callback.Callbacks):
    """An abstract base class for displaying tables represented by
    astropy table objects.

    Parameters
    ----------
    logger : :py:class:`~logging.Logger` or `None`
        Logger for tracing and debugging. If not given, one will be created.

    settings : `~ginga.misc.Settings.SettingGroup` or `None`
        Viewer preferences. If not given, one will be created.

    """

    vname = 'Ginga Table'
    vtypes = [AstroTable.AstroTable]

    def __init__(self, logger=None, settings=None):
        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('TableViewBase')

        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings

        # for debugging
        self.name = str(self)

        self.settings.addDefaults(color_alternate_rows=True,
                                  max_rows_for_col_resize=5000)

        # For callbacks
        for name in ('table-set', 'configure', ):
            self.enable_callback(name)

    def get_settings(self):
        """Get the settings used by this instance.

        Returns
        -------
        settings : `~ginga.misc.Settings.SettingGroup`
            Settings.

        """
        return self.settings

    def get_logger(self):
        """Get the logger used by this instance.

        Returns
        -------
        logger : :py:class:`~logging.Logger`
            Logger.

        """
        return self.logger

    def set_table(self, table):
        self._table = table

        self.make_callback('table-set', table)

    def get_table(self):
        return self._table

    # for compatibility with ImageView
    get_image = get_table
    set_image = set_table

    def initialize_channel(self, fv, channel):
        """The reference viewer calls this method with itself and the channel
        when it is inserted into a channel.
        """
        self.logger.warning("subclass should override this method")


class TableViewGw(TableViewBase):

    def __init__(self, logger=None, settings=None):
        super(TableViewGw, self).__init__(logger=logger, settings=settings)

        self.add_callback('table-set', self.set_table_cb)

        from ginga.gw import Widgets

        # Create the viewer as a Treeview widget
        color_alternate = self.settings.get('color_alternate_rows', True)
        self.widget = Widgets.TreeView(auto_expand=True,
                                       sortable=True,
                                       use_alt_row_color=color_alternate)

    def get_widget(self):
        return self.widget

    def set_table_cb(self, viewer, table):
        """Display the given table object."""
        self.clear()
        tree_dict = OrderedDict()

        # Extract data as astropy table
        a_tab = table.get_data()

        # Fill masked values, if applicable
        try:
            a_tab = a_tab.filled()
        except Exception:  # Just use original table
            pass

        # This is to get around table widget not sorting numbers properly
        i_fmt = '{{0:0{0}d}}'.format(len(str(len(a_tab))))

        # Table header with units
        columns = [('Row', '_DISPLAY_ROW')]
        for c in itervalues(a_tab.columns):
            col_str = '{0:^s}\n{1:^s}'.format(c.name, str(c.unit))
            columns.append((col_str, c.name))

        self.widget.setup_table(columns, 1, '_DISPLAY_ROW')

        # Table contents
        for i, row in enumerate(a_tab, 1):
            bnch = Bunch.Bunch(zip(row.colnames, row.as_void()))
            i_str = i_fmt.format(i)
            bnch['_DISPLAY_ROW'] = i_str
            tree_dict[i_str] = bnch

        self.widget.set_tree(tree_dict)

        # Resize column widths
        n_rows = len(tree_dict)
        if n_rows < self.settings.get('max_rows_for_col_resize', 5000):
            self.widget.set_optimal_column_widths()
            self.logger.debug('Resized columns for {0} row(s)'.format(n_rows))

        tablename = table.get('name', 'NoName')
        self.logger.debug('Displayed {0}'.format(tablename))

    def clear(self):
        self.widget.clear()

    def initialize_channel(self, fv, channel):
        # no housekeeping to do (for now) on our part, just override to
        # suppress the logger warning
        pass

# END
