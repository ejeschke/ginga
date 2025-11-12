#
# Plotable.py -- Abstraction of generic plot data.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.BaseImage import ViewerObjectBase, Header
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc.Bunch import Bunch


class Plotable(ViewerObjectBase):
    """Abstraction of a plot data.

    .. note:: This module is NOT thread-safe!

    """
    # class variables for WCS can be set
    wcsClass = None
    ioClass = None

    @classmethod
    def set_wcsClass(cls, klass):
        cls.wcsClass = klass

    @classmethod
    def set_ioClass(cls, klass):
        cls.ioClass = klass

    def __init__(self, data_ap=None, metadata=None, logger=None, name=None,
                 wcsclass=wcsClass, ioclass=ioClass):

        ViewerObjectBase.__init__(self, logger=logger, metadata=metadata,
                                  name=name)

        self.wcs = None
        self.io = None

        dc = get_canvas_types()
        self.canvas = dc.Canvas()
        self.titles = Bunch(title=None, x_axis=None, y_axis=None)
        self.grid = False
        self.rgb_order = 'RGBA'

    def get_size(self):
        return (self.columns, self.rows)

    def get_canvas(self):
        return self.canvas

    def get_header(self, create=True, include_primary_header=None):
        # By convention, the header is stored in a dictionary
        # under the metadata keyword 'header'
        if 'header' not in self:
            if not create:
                # TODO: change to ValueError("No header found")
                raise KeyError('header')

            hdr = Header()
            self.set(header=hdr)
        else:
            hdr = self['header']

        return hdr

    def has_primary_header(self):
        return False

    def set_titles(self, title=None, x_axis=None, y_axis=None):
        if x_axis is not None:
            self.titles.x_axis = x_axis
        if y_axis is not None:
            self.titles.y_axis = y_axis
        if title is not None:
            self.titles.title = title

    def set_grid(self, tf):
        self.grid = tf

    def clear(self):
        self.canvas.delete_all_objects()
        self.titles.x_axis = None
        self.titles.y_axis = None
        self.titles.title = None
        self.grid = False

    def get_minmax(self, noinf=False):
        # TODO: what should this mean for a plot?
        return (0, 0)

    def load_file(self, filespec):
        raise NotImplementedError("This method is not yet implemented")

    def get_thumbnail(self, length):
        thumb_np = np.eye(length)
        return thumb_np

    def info_xy(self, data_x, data_y, settings):
        info = super().info_xy(data_x, data_y, settings)

        ra_txt = "%+.3f" % (data_x)
        dec_txt = "%+.3f" % (data_y)
        ra_lbl, dec_lbl = "X", "Y"

        info.update(dict(itype='plotxy', ra_txt=ra_txt, dec_txt=dec_txt,
                         ra_lbl=ra_lbl, dec_lbl=dec_lbl))
        return info
