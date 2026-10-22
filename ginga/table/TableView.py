#
# TableView.py -- Table viewer for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from collections import OrderedDict
import numbers

import numpy as np

from ginga.util.viewer import ViewerBase
from ginga.table import AstroTable


def _thumb_font(px=9):
    """The smallest legible font we can count on being present."""
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=px)

    except TypeError:
        # Pillow older than 10.1 takes no size here
        return ImageFont.load_default()


def _fit_text(draw, text, font, max_wd):
    """Shorten `text` with an ellipsis until it fits in `max_wd` pixels."""
    if draw.textlength(text, font=font) <= max_wd:
        return text

    ellipsis = '\u2026'
    while len(text) > 0:
        text = text[:-1]
        if draw.textlength(text + ellipsis, font=font) <= max_wd:
            return text + ellipsis

    return ''


def _fmt_cell(val):
    """Render one table value short enough to be worth drawing."""
    if isinstance(val, (float, np.floating)):
        return '%.4g' % (val,)

    text = str(val)
    return text if len(text) <= 24 else text[:24]


def table_preview(tbl, max_rows, max_cols):
    """Pull the top-left corner out of a table, as strings.

    Returns a 4-tuple of the column names used, a list of rows of
    formatted cell values, and the table's full row and column counts.
    Tolerant of a table it cannot read, in which case the counts come
    back as 0 and there are no cells: a thumbnail is not worth raising
    over.
    """
    try:
        a_tab = tbl.get_data()

    except Exception:
        a_tab = None

    colnames = list(getattr(a_tab, 'colnames', None) or
                    getattr(tbl, 'colnames', None) or [])
    try:
        n_rows = len(a_tab)

    except Exception:
        n_rows = 0

    use_cols = colnames[:max_cols]
    cells = []
    for i in range(min(n_rows, max_rows)):
        try:
            row = a_tab[i]
            cells.append([_fmt_cell(row[name]) for name in use_cols])

        except Exception:
            cells.append([''] * len(use_cols))

    return use_cols, cells, n_rows, len(colnames)


def draw_table_thumbnail(tbl, size, logger=None):
    """Draw a thumbnail showing what is in the table `tbl`.

    Parameters
    ----------
    tbl : `~ginga.table.AstroTable.AstroTable` or `None`
        The table to draw.

    size : tuple of (int, int)
        The (width, height) of the thumbnail, in pixels.

    Returns
    -------
    arr_np : ndarray
        An RGB array of shape (ht, wd, 3) and dtype uint8.

    A photograph of a table widget shrunk to thumbnail size is a few grey
    stripes, and taking one needs the widget to exist and be on screen --
    which is backend-specific, and false exactly when the table is not
    what the user is looking at.  Drawing the table instead gives
    something that says which table this is, on every backend, whether or
    not it is on screen.
    """
    from PIL import Image as PILImage, ImageDraw

    wd, ht = max(24, int(size[0])), max(24, int(size[1]))

    c_page = (250, 250, 251)
    c_border = (138, 154, 168)
    c_header = (74, 103, 133)
    c_header_fg = (255, 255, 255)
    c_row = ((255, 255, 255), (237, 241, 246))
    c_grid = (214, 221, 228)
    c_text = (48, 56, 64)
    c_footer = (226, 230, 235)
    c_footer_fg = (90, 100, 112)

    img = PILImage.new('RGB', (wd, ht), c_page)
    draw = ImageDraw.Draw(img)
    font = _thumb_font()
    asc, desc = font.getmetrics()
    line_ht = max(7, asc + desc)
    row_ht = line_ht + 2
    band_ht = line_ht + 4

    # how many columns can be drawn before they stop meaning anything
    min_col_wd = 30
    max_cols = max(1, (wd - 2) // min_col_wd)
    body_ht = max(0, ht - 2 - band_ht * 2)
    max_rows = max(0, body_ht // row_ht)

    use_cols, cells, n_rows, n_cols = table_preview(tbl, max_rows, max_cols)
    if logger is not None:
        logger.debug("table thumb: %dx%d, drawing %d col(s), %d row(s)" % (
            n_rows, n_cols, len(use_cols), len(cells)))

    n_draw_cols = max(1, len(use_cols))
    col_wd = (wd - 2) / n_draw_cols
    pad = 2

    # header band: the column names
    draw.rectangle([0, 0, wd - 1, band_ht], fill=c_header)
    for j, name in enumerate(use_cols):
        x = 1 + j * col_wd
        draw.text((x + pad, 2),
                  _fit_text(draw, str(name), font, col_wd - 2 * pad),
                  font=font, fill=c_header_fg)

    # body: alternating rows of values, with column rules
    y = band_ht + 1
    for i in range(max_rows):
        if y + row_ht > ht - band_ht:
            break
        draw.rectangle([1, y, wd - 2, y + row_ht - 1], fill=c_row[i % 2])
        if i < len(cells):
            for j, text in enumerate(cells[i]):
                x = 1 + j * col_wd
                draw.text((x + pad, y + 1),
                          _fit_text(draw, text, font, col_wd - 2 * pad),
                          font=font, fill=c_text)
        y += row_ht

    for j in range(1, n_draw_cols):
        x = int(1 + j * col_wd)
        draw.line([x, band_ht + 1, x, y - 1], fill=c_grid)

    # footer band: the shape of the whole table, which the corner we drew
    # gives no clue about
    y_foot = ht - band_ht - 1
    draw.rectangle([0, y_foot, wd - 1, ht - 1], fill=c_footer)
    # the corner we drew says nothing about how big the table is.
    # NOTE: stay in ASCII -- Pillow's default bitmap font has no glyph for
    # 'x' as a multiplication sign, and draws a hollow box instead.
    avail = wd - 2 * pad
    shape = '%d rows x %d cols' % (n_rows, n_cols)
    if draw.textlength(shape, font=font) > avail:
        shape = '%d x %d' % (n_rows, n_cols)
    draw.text((pad, y_foot + 2), _fit_text(draw, shape, font, avail),
              font=font, fill=c_footer_fg)

    draw.rectangle([0, 0, wd - 1, ht - 1], outline=c_border)

    return np.asarray(img, dtype=np.uint8)


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

    def get_thumbnail_array(self, dataobj, size):
        """Draw a thumbnail of the table `dataobj`.  See
        `~ginga.util.viewer.ViewerBase.get_thumbnail_array`.

        Drawn from the table rather than captured from the table widget,
        so it works on every backend and for any table -- not only the
        one this viewer happens to be showing.
        """
        if not isinstance(dataobj, AstroTable.AstroTable):
            return None

        try:
            return draw_table_thumbnail(dataobj, size, logger=self.logger)

        except Exception as e:
            self.logger.warning("Error drawing table thumbnail: %s" % (
                str(e)))
            return None


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

    def get_widget(self):
        return self.widget

    def _get_table_type(self, val):
        # bool before the numbers: Python's bool is an int.  Array-valued
        # cells (vector columns) are none of these and display as 'str'.
        if isinstance(val, (bool, np.bool_)):
            return 'bool'
        elif isinstance(val, numbers.Integral):
            return 'int'
        elif isinstance(val, numbers.Number):
            return 'float'
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
        """Get a numpy RGB array depicting this table.

        Drawn, not captured from the table widget: see
        `draw_table_thumbnail`.
        """
        try:
            size = self.get_window_size()

        except Exception:
            size = (240, 240)

        return draw_table_thumbnail(self.get_table(), size,
                                    logger=self.logger)
