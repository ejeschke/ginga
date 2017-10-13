#
# BaseImage.py -- Abstraction of an generic data image.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.util.six.moves import map

import numpy as np
import logging

from ginga.misc import Bunch, Callback
from ginga import trcalc, AutoCuts


class ImageError(Exception):
    pass


class ViewerObjectBase(Callback.Callbacks):

    def __init__(self, metadata=None, logger=None, name=None):

        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('BaseImage')
        self.metadata = {}
        if metadata:
            self.update_metadata(metadata)
        # make sure an object has these attributes
        # TODO: this maybe should have a unique random string or something
        # but we'd have to fix a lot of code that is currently checking for
        # None
        self.metadata.setdefault('name', None)

        # For callbacks
        for name in ('modified', ):
            self.enable_callback(name)

    def get_metadata(self):
        return self.metadata.copy()

    def clear_metadata(self):
        self.metadata = {}

    def clear_all(self):
        self.clear_metadata()

    def update_metadata(self, map_like):
        for key, val in map_like.items():
            self.metadata[key] = val

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


class BaseImage(ViewerObjectBase):

    def __init__(self, data_np=None, metadata=None, logger=None, order=None,
                 name=None):

        ViewerObjectBase.__init__(self, logger=logger, metadata=metadata,
                                  name=name)

        if data_np is None:
            data_np = np.zeros((1, 1))
        self._data = data_np
        self.order = ''
        self.name = name

        self._set_minmax()
        self._calc_order(order)

        self.autocuts = AutoCuts.Histogram(self.logger)

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

    @property
    def dtype(self):
        return self._get_data().dtype

    def get_size(self):
        return (self.width, self.height)

    def get_depth(self):
        shape = self.shape
        if len(shape) > 2:
            return shape[-1]
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
        for fast calculation of the intensity distribution.

        NOTE: this is used by the Ginga plugin for Glue
        """
        return self._data

    def copy_data(self):
        data = self._get_data()
        return data.copy()

    def get_data_xy(self, x, y):
        assert (x >= 0) and (y >= 0), \
            ImageError("Indexes out of range: (x=%d, y=%d)" % (
                x, y))
        view = np.s_[y, x]
        return self._slice(view)

    def set_data(self, data_np, metadata=None, order=None, astype=None):
        """Use this method to SHARE (not copy) the incoming array.
        """
        if astype:
            data = data_np.astype(astype)
        else:
            data = data_np
        self._data = data

        self._calc_order(order)

        if metadata:
            self.update_metadata(metadata)

        self._set_minmax()

        self.make_callback('modified')

    def clear_all(self):
        # clear metadata
        super(BaseImage, self).clear_all()

        # unreference data array
        self._data = np.zeros((1, 1))

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
        return np.dstack(l)

    def set_order(self, order):
        self.order = order.upper()

    def get_order(self):
        return self.order

    def get_order_indexes(self, cs):
        cs = cs.upper()
        return [self.order.index(c) for c in cs]

    def _calc_order(self, order):
        if order is not None and order != '':
            self.order = order.upper()
        else:
            shape = self.shape
            if len(shape) <= 2:
                self.order = 'M'
            elif self.dtype != np.uint8:
                self.order = 'M'
            else:
                depth = shape[-1]
                # TODO; need something better here than a guess!
                if depth == 1:
                    self.order = 'M'
                elif depth == 2:
                    self.order = 'AM'
                elif depth == 3:
                    self.order = 'RGB'
                elif depth == 4:
                    self.order = 'RGBA'

    def has_valid_wcs(self):
        return hasattr(self, 'wcs') and self.wcs.has_valid_wcs()

    def _set_minmax(self):
        data = self._get_fast_data()
        try:
            self.maxval = np.nanmax(data)
            self.minval = np.nanmin(data)
        except Exception:
            self.maxval = 0
            self.minval = 0

        # TODO: see if there is a faster way to ignore infinity
        try:
            if np.isfinite(self.maxval):
                self.maxval_noinf = self.maxval
            else:
                self.maxval_noinf = np.nanmax(data[np.isfinite(data)])
        except Exception:
            self.maxval_noinf = self.maxval

        try:
            if np.isfinite(self.minval):
                self.minval_noinf = self.minval
            else:
                self.minval_noinf = np.nanmin(data[np.isfinite(data)])
        except Exception:
            self.minval_noinf = self.minval

    def get_minmax(self, noinf=False):
        if not noinf:
            return (self.minval, self.maxval)
        else:
            return (self.minval_noinf, self.maxval_noinf)

    def get_header(self):
        return self.get('header', Header())

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
        view = np.s_[y1:y2:ystep, x1:x2:xstep]
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
        return self.cutout_adjust(x - radius, y - radius,
                                  x + radius + 1, y + radius + 1,
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

        xview = np.s_[y, x0:x1 + 1]
        yview = np.s_[y0:y1 + 1, x]

        xarr = self._slice(xview)
        yarr = self._slice(yview)

        return (x0, y0, xarr, yarr)

    def get_shape_mask(self, shape_obj):
        """
        Return full mask where True marks pixels within the given shape.
        """
        wd, ht = self.get_size()
        yi = np.mgrid[:ht].reshape(-1, 1)
        xi = np.mgrid[:wd].reshape(1, -1)
        pts = np.asarray((xi, yi)).T
        contains = shape_obj.contains_pts(pts)
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
            x1, x2 = max(0, x1), min(x2, wd - 1)
            y1, y2 = max(0, y1), min(y2, ht - 1)

        # calculate pixel containment mask in bbox
        yi = np.mgrid[y1:y2 + 1].reshape(-1, 1)
        xi = np.mgrid[x1:x2 + 1].reshape(1, -1)
        pts = np.asarray((xi, yi)).T
        contains = shape_obj.contains_pts(pts)

        view = np.s_[y1:y2 + 1, x1:x2 + 1]
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
        mdata = np.ma.array(data, mask=np.logical_not(mask))
        return mdata

    def get_scaled_cutout_wdht(self, x1, y1, x2, y2, new_wd, new_ht,
                               method='basic'):
        """Extract a region of the image defined by corners (x1, y1) and
        (x2, y2) and resample it to fit dimensions (new_wd, new_ht).

        `method` describes the method of interpolation used, where the
        default "basic" is nearest neighbor.
        """

        if method in ('basic', 'view'):
            shp = self.shape

            (view, (scale_x, scale_y)) = \
                trcalc.get_scaled_cutout_wdht_view(shp, x1, y1, x2, y2,
                                                   new_wd, new_ht)
            newdata = self._slice(view)

        else:
            data_np = self._get_data()
            (newdata, (scale_x, scale_y)) = \
                trcalc.get_scaled_cutout_wdht(data_np, x1, y1, x2, y2,
                                              new_wd, new_ht,
                                              interpolation=method,
                                              logger=self.logger)

        res = Bunch.Bunch(data=newdata, scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout_basic(self, x1, y1, x2, y2, scale_x, scale_y,
                                method='basic'):
        """Extract a region of the image defined by corners (x1, y1) and
        (x2, y2) and scale it by scale factors (scale_x, scale_y).

        `method` describes the method of interpolation used, where the
        default "basic" is nearest neighbor.
        """

        new_wd = int(round(scale_x * (x2 - x1 + 1)))
        new_ht = int(round(scale_y * (y2 - y1 + 1)))

        return self.get_scaled_cutout_wdht(x1, y1, x2, y2, new_wd, new_ht,
                                           # TODO:
                                           # this causes a problem for the
                                           # current Glue plugin--update that
                                           #method=method
                                           )

    def get_scaled_cutout(self, x1, y1, x2, y2, scale_x, scale_y,
                          method='basic', logger=None):
        if method == 'basic':
            return self.get_scaled_cutout_basic(x1, y1, x2, y2,
                                                scale_x, scale_y)

        data = self._get_data()
        newdata, (scale_x, scale_y) = trcalc.get_scaled_cutout_basic(
            data, x1, y1, x2, y2, scale_x, scale_y, interpolation=method)

        res = Bunch.Bunch(data=newdata, scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout2(self, p1, p2, scales,
                           method='basic', logger=None):

        if method not in ('basic',) and len(scales) == 2:
            # for 2D images with alternate interpolation requirements
            return self.get_scaled_cutout(p1[0], p1[1], p2[0], p2[1],
                                          scales[0], scales[1],
                                          method=method)

        shp = self.shape

        view, scales = trcalc.get_scaled_cutout_basic_view(
            shp, p1, p2, scales)

        newdata = self._slice(view)

        scale_x, scale_y = scales[:2]
        res = Bunch.Bunch(data=newdata, scale_x=scale_x, scale_y=scale_y)
        if len(scales) > 2:
            res.scale_z = scales[2]

        return res

    def get_thumbnail(self, length):
        wd, ht = self.get_size()
        if ht == 0:
            width, height = 1, 1
        elif wd > ht:
            width, height = length, int(length * float(ht) / wd)
        else:
            width, height = int(length * float(wd) / ht), length

        res = self.get_scaled_cutout_wdht(0, 0, wd, ht, width, height)
        return res.data

    def get_pixels_on_line(self, x1, y1, x2, y2, getvalues=True):
        """Uses Bresenham's line algorithm to enumerate the pixels along
        a line.
        (see http://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm)

        If `getvalues`==False then it will return tuples of (x, y) coordinates
        instead of pixel values.
        """
        # NOTE: seems to be necessary or we get a non-terminating result
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

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
                    val = np.NaN
                res.append(val)
            else:
                res.append((x, y))
            if (x == x2) and (y == y2):
                break
            e2 = 2 * err
            if e2 > -dy:
                err = err - dy
                x += sx
            if e2 < dx:
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

    def set_card(self, key, value, comment=None):
        try:
            bnch = super(Header, self).__getitem__(key)
            bnch.value = value
            if not (comment is None):
                bnch.comment = comment
        except KeyError:
            if comment is None:
                comment = ''
            bnch = Bunch.Bunch(key=key, value=value, comment=comment)
            self.keyorder.append(key)
            super(Header, self).__setitem__(key, bnch)
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

    def update(self, map_kind):
        for key, value in map_kind.items():
            self.__setitem__(key, value)

    def asdict(self):
        return dict([(key, self[key]) for key in self.keys()])

# END
