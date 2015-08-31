#
# BaseImage.py -- Abstraction of an generic data image.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy
import logging

from ginga.misc import Bunch, Callback
from ginga import trcalc, AutoCuts
from ginga.util.six.moves import map, zip

class ImageError(Exception):
    pass

class BaseImage(Callback.Callbacks):

    def __init__(self, data_np=None, metadata=None, logger=None):

        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('BaseImage')
        if data_np is None:
            data_np = numpy.zeros((1, 1))
        self._data = data_np
        self.metadata = {}
        if metadata:
            self.update_metadata(metadata)
        self.order = ''

        self._set_minmax()

        self.autocuts = AutoCuts.Histogram(self.logger)

        # For callbacks
        for name in ('modified', ):
            self.enable_callback(name)

    @property
    def shape(self):
        return self._get_data().shape

    @property
    def width(self):
        # NOTE: numpy stores data in column-major layout
        return self.shape[1]

    @property
    def height(self):
        # NOTE: numpy stores data in column-major layout
        return self.shape[0]

    @property
    def depth(self):
        return self.get_depth()

    @property
    def ndim(self):
        return len(self.shape)

    def get_size(self):
        return (self.width, self.height)

    def get_depth(self):
        shape = self.shape
        if len(shape) > 2:
            return shape[2]
        return 1

    def get_shape(self):
        return self.shape

    def get_center(self):
        wd, ht = self.get_size()
        ctr_x, ctr_y = wd // 2, ht // 2
        return (ctr_x, ctr_y)

    def get_data(self):
        return self._data

    def _get_data(self):
        return self._data

    def _get_fast_data(self):
        """
        Return an array similar to but possibly smaller than self._data,
        for fast calculation of the intensity distribution
        """
        return self._data

    def copy_data(self):
        data = self._get_data()
        return data.copy()

    def get_data_xy(self, x, y):
        assert (x >= 0) and (y >= 0), \
            ImageError("Indexes out of range: (x=%d, y=%d)" % (
                x, y))
        view = numpy.s_[y, x]
        return self._slice(view)

    def get_metadata(self):
        return self.metadata.copy()

    def get_header(self):
        return self.get('header', Header())

    def get(self, kwd, *args):
        if kwd in self.metadata:
            return self.metadata[kwd]
        else:
            # return a default if there is one
            if len(args) > 0:
                return args[0]
            raise KeyError(kwd)

    def get_list(self, *args):
        return list(map(self.get, args))

    def __getitem__(self, kwd):
        return self.metadata[kwd]

    def update(self, kwds):
        self.metadata.update(kwds)

    def set(self, **kwds):
        self.update(kwds)

    def __setitem__(self, kwd, value):
        self.metadata[kwd] = value

    def set_data(self, data_np, metadata=None, astype=None):
        """Use this method to SHARE (not copy) the incoming array.
        """
        if astype:
            data = data_np.astype(astype)
        else:
            data = data_np
        self._data = data

        if metadata:
            self.update_metadata(metadata)

        self._set_minmax()

        self.make_callback('modified')

    def _slice(self, view):
        return self._get_data()[view]

    def get_slice(self, c):
        view = [slice(None)] * self.ndim
        view[-1] = self.order.index(c.upper())
        return self._slice(view)

    def has_slice(self, c):
        return c.upper() in self.order

    def get_array(self, order):
        order = order.upper()
        if order == self.order:
            return self._get_data()
        l = [self.get_slice(c) for c in order]
        return numpy.dstack(l)

    def set_order(self, order):
        self.order = order.upper()

    def get_order(self):
        return self.order

    def get_order_indexes(self, cs):
        cs = cs.upper()
        return [ self.order.index(c) for c in cs ]

    def has_valid_wcs(self):
        return hasattr(self, 'wcs') and self.wcs.has_valid_wcs()

    def _set_minmax(self):
        data = self._get_fast_data()
        try:
            self.maxval = numpy.nanmax(data)
            self.minval = numpy.nanmin(data)
        except Exception:
            self.maxval = 0
            self.minval = 0

        # TODO: see if there is a faster way to ignore infinity
        try:
            if numpy.isfinite(self.maxval):
                self.maxval_noinf = self.maxval
            else:
                self.maxval_noinf = numpy.nanmax(data[numpy.isfinite(data)])
        except:
            self.maxval_noinf = self.maxval

        try:
            if numpy.isfinite(self.minval):
                self.minval_noinf = self.minval
            else:
                self.minval_noinf = numpy.nanmin(data[numpy.isfinite(data)])
        except:
            self.minval_noinf = self.minval

    def get_minmax(self, noinf=False):
        if not noinf:
            return (self.minval, self.maxval)
        else:
            return (self.minval_noinf, self.maxval_noinf)

    def update_metadata(self, keyDict):
        for key, val in keyDict.items():
            self.metadata[key] = val

    def transfer(self, other, astype=None):
        data = self._get_data()
        other.set_data(data, metadata=self.metadata, astype=astype)

    def copy(self, astype=None):
        data = self.copy_data()
        metadata = self.get_metadata()
        other = self.__class__(data_np=data, metadata=metadata)
        return other

    def cutout_data(self, x1, y1, x2, y2, xstep=1, ystep=1, astype=None):
        """cut out data area based on coords.
        """
        view = numpy.s_[y1:y2:ystep, x1:x2:xstep]
        data = self._slice(view)
        if astype:
            data = data.astype(astype)
        return data

    def cutout_adjust(self, x1, y1, x2, y2, xstep=1, ystep=1, astype=None):
        dx = x2 - x1
        dy = y2 - y1

        if x1 < 0:
            x1, x2 = 0, dx
        else:
            if x2 >= self.width:
                x2 = self.width
                x1 = x2 - dx

        if y1 < 0:
            y1, y2 = 0, dy
        else:
            if y2 >= self.height:
                y2 = self.height
                y1 = y2 - dy

        data = self.cutout_data(x1, y1, x2, y2, xstep=xstep, ystep=ystep,
                                astype=astype)
        return (data, x1, y1, x2, y2)

    def cutout_radius(self, x, y, radius, xstep=1, ystep=1, astype=None):
        return self.cutout_adjust(x-radius, y-radius,
                                  x+radius+1, y+radius+1,
                                  xstep=xstep, ystep=ystep,
                                  astype=astype)

    def cutout_cross(self, x, y, radius):
        """Cut two data subarrays that have a center at (x, y) and with
        radius (radius) from (image).  Returns the starting pixel (x0, y0)
        of each cut and the respective arrays (xarr, yarr).
        """
        n = radius
        wd, ht = self.get_size()
        x0, x1 = max(0, x - n), min(wd - 1, x + n)
        y0, y1 = max(0, y - n), min(ht - 1, y + n)

        xview = numpy.s_[y, x0:x1 + 1]
        yview = numpy.s_[y0:y1 + 1, x]

        xarr = self._slice(xview)
        yarr = self._slice(yview)

        return (x0, y0, xarr, yarr)

    def get_shape_mask(self, shape_obj):
        """
        Return full mask where True marks pixels within the given shape.
        """
        wd, ht = self.get_size()
        yi = numpy.mgrid[:ht].reshape(-1, 1)
        xi = numpy.mgrid[:wd].reshape(1, -1)
        contains = shape_obj.contains_arr(xi, yi)
        return contains

    def get_shape_view(self, shape_obj, avoid_oob=True):
        """
        Calculate a bounding box in the data enclosing `shape_obj` and
        return a view that accesses it and a mask that is True only for
        pixels enclosed in the region.

        If `avoid_oob` is True (default) then the bounding box is clipped
        to avoid coordinates outside of the actual data.
        """
        x1, y1, x2, y2 = map(int, shape_obj.get_llur())

        if avoid_oob:
            # avoid out of bounds indexes
            wd, ht = self.get_size()
            x1, x2 = max(0, x1), min(x2, wd-1)
            y1, y2 = max(0, y1), min(y2, ht-1)

        # calculate pixel containment mask in bbox
        yi = numpy.mgrid[y1:y2+1].reshape(-1, 1)
        xi = numpy.mgrid[x1:x2+1].reshape(1, -1)
        contains = shape_obj.contains_arr(xi, yi)

        view = numpy.s_[y1:y2+1, x1:x2+1]
        return (view, contains)

    def cutout_shape(self, shape_obj):
        """
        Cut out and return a portion of the data corresponding to `shape_obj`.
        A masked numpy array is returned, where the pixels not enclosed in
        the shape are masked out.
        """

        view, mask = self.get_shape_view(shape_obj)

        # cutout our enclosing (possibly shortened) bbox
        data = self._slice(view)

        # mask non-containing members
        mdata = numpy.ma.array(data, mask=numpy.logical_not(mask))
        return mdata

    def get_scaled_cutout_wdht(self, x1, y1, x2, y2, new_wd, new_ht):

        shp = self.shape

        (view, (scale_x, scale_y)) = \
            trcalc.get_scaled_cutout_wdht_view(shp, x1, y1, x2, y2,
                                               new_wd, new_ht)
        newdata = self._slice(view)

        res = Bunch.Bunch(data=newdata, scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout_basic(self, x1, y1, x2, y2, scale_x, scale_y):
        new_wd = int(round(scale_x * (x2 - x1 + 1)))
        new_ht = int(round(scale_y * (y2 - y1 + 1)))
        return self.get_scaled_cutout_wdht(x1, y1, x2, y2, new_wd, new_ht)

    def get_scaled_cutout_by_dims(self, x1, y1, x2, y2, dst_wd, dst_ht,
                                  method='basic'):
        if method == 'basic':
            return self.get_scaled_cutout_wdht(x1, y1, x2, y2, dst_wd, dst_ht)

        data = self._get_data()
        newdata, (scale_x, scale_y) = trcalc.get_scaled_cutout_wdht(
            data, x1, y1, x2, y2, dst_wd, dst_ht, interpolation=method)

        res = Bunch.Bunch(data=newdata, scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout(self, x1, y1, x2, y2, scale_x, scale_y,
                          method='basic'):
        if method == 'basic':
            return self.get_scaled_cutout_basic(x1, y1, x2, y2,
                                                scale_x, scale_y)

        data = self._get_data()
        newdata, (scale_x, scale_y) = trcalc.get_scaled_cutout_basic(
            data, x1, y1, x2, y2, scale_x, scale_y, interpolation=method)

        res = Bunch.Bunch(data=newdata, scale_x=scale_x, scale_y=scale_y)
        return res

    def get_pixels_on_line(self, x1, y1, x2, y2, getvalues=True):
        """Uses Bresenham's line algorithm to enumerate the pixels along
        a line.
        (see http://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm)

        If `getvalues`==False then it will return tuples of (x, y) coordinates
        instead of pixel values.
        """
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if x1 < x2:
            sx = 1
        else:
            sx = -1
        if y1 < y2:
            sy = 1
        else:
            sy = -1
        err = dx - dy

        res = []
        x, y = x1, y1
        while True:
            if getvalues:
                try:
                    val = self.get_data_xy(x, y)
                except Exception:
                    val = numpy.NaN
                res.append(val)
            else:
                res.append((x, y))
            if (x == x2) and (y == y2):
                break
            e2 = 2 * err
            if e2 > -dy:
                err = err - dy
                x += sx
            if e2 <  dx:
                err = err + dx
                y += sy

        return res


    def info_xy(self, data_x, data_y, settings):
        # Get the value under the data coordinates
        try:
            value = self.get_data_xy(int(data_x), int(data_y))

        except Exception as e:
            value = None

        info = Bunch.Bunch(itype='base', data_x=data_x, data_y=data_y,
                           x=data_x, y=data_y,
                           value=value)
        return info


class Header(dict):

    def __init__(self, *args, **kwdargs):
        super(Header, self).__init__(*args, **kwdargs)
        self.keyorder = []

    def __getitem__(self, key):
        bnch = super(Header, self).__getitem__(key)
        return bnch.value

    def __setitem__(self, key, value):
        try:
            bnch = super(Header, self).__getitem__(key)
            bnch.value = value
        except KeyError:
            bnch = Bunch.Bunch(key=key, value=value, comment='')
            self.keyorder.append(key)
            super(Header, self).__setitem__(key, bnch)
        return bnch

    def __delitem__(self, key):
        super(Header, self).__delitem__(key)
        self.keyorder.remove(key)

    def get_card(self, key):
        bnch = super(Header, self).__getitem__(key)
        return bnch

    def get_keyorder(self):
        return self.keyorder

    def keys(self):
        return self.keyorder

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def get(self, key, alt=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return alt

    def update(self, mapKind):
        for key, value in mapKind.items():
            self.__setitem__(key, value)

    def asdict(self):
        return dict([(key, self[key]) for key in self.keys()])

#END
