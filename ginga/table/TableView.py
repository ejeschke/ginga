#
# TableView.py -- Table viewer for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from collections import OrderedDict
import os.path
import numbers

import numpy as np

from ginga.util.viewer import ViewerBase
from ginga.util.paths import icondir
from ginga.table import AstroTable
from ginga.util.io import io_rgb


class TableViewBase(ViewerBase):
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

    @classmethod
    def viewable(cls, dataobj):
        """Test whether `dataobj` is viewable by this viewer."""
        if not isinstance(dataobj, AstroTable.AstroTable):
            return False
        return True

    def __init__(self, logger=None, settings=None):
        ViewerBase.__init__(self, logger=logger, settings=settings)

        self._table = None

        self.settings.add_defaults(color_alternate_rows=True,
                                   max_rows_for_col_resize=5000)

        # no specific UI modes for this viewer
        self.set_allowed_modes([])

        # For callbacks
        for name in ('table-set', 'configure', ):
            self.enable_callback(name)

    def set_table(self, table):
        if not isinstance(table, AstroTable.AstroTable):
            raise ValueError("Wrong type of object to load: %s" % (
                str(type(table))))

        self._table = table

        self.make_callback('table-set', table)

    def get_table(self):
        return self._table

    # for compatibility with other Ginga viewers
    get_dataobj = get_table
    set_dataobj = set_table


class TableViewGw(TableViewBase):
    """A Ginga viewer for displaying tables of FITS data.
    """

    def __init__(self, logger=None, settings=None):
        super(TableViewGw, self).__init__(logger=logger, settings=settings)

        self.add_callback('table-set', self.set_table_cb)

        from ginga.gw import Widgets

        # Create the viewer as a Treeview widget
        color_alternate = self.settings.get('color_alternate_rows', True)
        self.widget = Widgets.TreeView(auto_expand=True,
                                       sortable=True,
                                       use_alt_row_color=color_alternate)

        rgb_opener = io_rgb.RGBFileHandler(self.logger)
        tmp_path = os.path.join(icondir, 'fits.png')
        placeholder_image = rgb_opener.load_file(tmp_path)
        self._rgb_array_placeholder = placeholder_image.get_data()

    def get_widget(self):
        return self.widget

    def _get_table_type(self, val):
        if isinstance(val, numbers.Number):
            if isinstance(val, int):
                return 'int'
            else:
                return 'float'
        elif isinstance(val, bool) or val in [np.True_, np.False_]:
            return 'bool'
        else:
            return 'str'

    def set_table_cb(self, viewer, table):
        """Display the given table object."""
        self.clear()
        tree_dict = OrderedDict()

        # Extract data as astropy table
        a_tab = table.get_data()

        columns = [('Row', '_DISPLAY_ROW', 'str')]

        # This is to get around some table widget implementations
        # not sorting numbers properly
        i_fmt = '{{0:0{0}d}}'.format(len(str(table.rows)))

        if table.kind == 'table-astropy':
            # Fill masked values, if applicable
            try:
                a_tab = a_tab.filled()
            except Exception:  # Just use original table
                pass

            # Table header with units
            row = a_tab[0]
            for i, c in enumerate(a_tab.columns.values()):
                col_str = '{0:^s}\n{1:^s}'.format(c.name, str(c.unit)) \
                    if c.unit is not None else '{0:^s}'.format(c.name)
                _data_type = self._get_table_type(row[i])
                columns.append((col_str, c.name, _data_type))

            # Table contents
            for i, row in enumerate(a_tab, 1):
                row_dct = dict(zip(row.colnames, row.as_void()))
                i_str = i_fmt.format(i)
                row_dct['_DISPLAY_ROW'] = i_str
                tree_dict[i_str] = row_dct

        elif table.kind == 'table-fitsio':
            colnames = table.colnames

            # Table header
            row = a_tab[0]
            for c_name in colnames:
                col_str = '{0:^s}'.format(c_name)
                _data_type = self._get_table_type(row[i])
                columns.append((col_str, c_name, _data_type))

            # Table contents
            for i, row in enumerate(a_tab, 1):
                row_dct = dict(zip(colnames, row))
                i_str = i_fmt.format(i)
                row_dct['_DISPLAY_ROW'] = i_str
                tree_dict[i_str] = row_dct

        else:
            raise ValueError(f"I don't know how to display tables of type '{table.kind}'")

        self.widget.setup_table(columns, 1, '_DISPLAY_ROW')
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

    def get_data_size(self):
        return (1, 1)

    def get_last_data_xy(self):
        return (0, 0)

    def get_window_size(self):
        return self.widget.get_size()

    def get_rgb_array(self):
        if not hasattr(self.widget, 'get_rgb_array'):
            return self._rgb_array_placeholder

        return self.widget.get_rgb_array()
