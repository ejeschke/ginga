#
# transform.py -- coordinate transforms for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc
from ginga.misc import Bunch

__all__ = ['TransformError', 'BaseTransform', 'ComposedTransform',
           'InvertedTransform', 'PassThruTransform',
           'WindowNativeTransform', 'CartesianWindowTransform',
           'CartesianNativeTransform',
           'RotationTransform', 'ScaleTransform',
           'DataCartesianTransform', 'OffsetDataTransform',
           'WCSDataTransform', 'get_catalog'
           ]


class TransformError(Exception):
    pass


class BaseTransform(object):

    def __init__(self):
        super(BaseTransform, self).__init__()

    def to_(self, x, y):
        raise TransformError("subclass should override this method")

    def from_(self, tx, ty):
        raise TransformError("subclass should override this method")

    def __add__(self, trans):
        return ComposedTransform(self, trans)

    @classmethod
    def inverted_class(cls):
        class _inverted(cls):

            def __init__(self, *args, **kwargs):
                cls.__init__(self, *args, **kwargs)

            def to_(self, pts, **kwargs):
                return cls.from_(self, pts, **kwargs)

            def from_(self, pts, **kwargs):
                return cls.to_(self, pts, **kwargs)

        return _inverted

    def invert(self):
        return self.inverted_class()(self)


class ComposedTransform(BaseTransform):
    """
    A transform that composes two other transforms to make a new one.
    """

    def __init__(self, tform1, tform2):
        super(ComposedTransform, self).__init__()
        self.tform1 = tform1
        self.tform2 = tform2

    def to_(self, pts, **kwargs):
        return self.tform2.to_(self.tform1.to_(pts, **kwargs))

    def from_(self, pts, **kwargs):
        return self.tform1.from_(self.tform2.from_(pts), **kwargs)


class InvertedTransform(BaseTransform):
    """
    A transform that inverts another transform.
    """

    def __init__(self, tform):
        super(InvertedTransform, self).__init__()
        self.tform = tform

    def to_(self, pts, **kwargs):
        return self.tform.from_(pts, **kwargs)

    def from_(self, pts, **kwargs):
        return self.tform.to_(pts, **kwargs)


class PassThruTransform(BaseTransform):
    """
    A transform that essentially acts as a no-op.
    """

    def __init__(self, viewer):
        super(PassThruTransform, self).__init__()

    def to_(self, pts, **kwargs):
        return pts

    def from_(self, pts, **kwargs):
        return pts


class WindowNativeTransform(BaseTransform):
    """
    A transform from a typical window standard coordinate space with the
    upper left at (0, 0) to the viewer back end native pixel space.
    """

    def __init__(self, viewer):
        super(WindowNativeTransform, self).__init__()
        self.viewer = viewer

    def to_(self, win_pts):
        if self.viewer.origin_upper:
            return win_pts

        win_pts = np.asarray(win_pts)
        has_z = (win_pts.shape[-1] > 2)

        # invert Y coord for backends that have the origin in the lower left
        win_wd, win_ht = self.viewer.get_window_size()

        # win_x, win_y = cvs_x, win_ht - cvs_y
        mpy_pt = [1.0, -1.0]
        if has_z:
            mpy_pt.append(1.0)

        add_pt = [0.0, win_ht]
        if has_z:
            add_pt.append(0.0)

        ntv_pts = np.add(np.multiply(win_pts, mpy_pt), add_pt)

        return ntv_pts

    def from_(self, ntv_pts):
        return self.to_(ntv_pts)


class CartesianWindowTransform(BaseTransform):
    """
    A transform from cartesian coordinates to standard window coordinates
    of a viewer.
    """

    def __init__(self, viewer, as_int=True):
        super(CartesianWindowTransform, self).__init__()
        self.viewer = viewer
        self.as_int = as_int

    def to_(self, off_pts):
        # add center pixel to convert from X/Y coordinate space to
        # window graphics space
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        ctr_pt = list(self.viewer.get_center())
        if has_z:
            ctr_pt.append(0.0)

        # win_x = off_x + ctr_x
        # win_y = ctr_y - off_y
        mpy_pt = [1.0, -1.0]
        if has_z:
            mpy_pt.append(1.0)

        win_pts = np.add(np.multiply(off_pts, mpy_pt), ctr_pt)

        # round to pixel units, if asked
        if self.as_int:
            win_pts = np.rint(win_pts).astype(np.int, copy=False)

        return win_pts

    def from_(self, win_pts):
        """Reverse of :meth:`to_`."""
        # make relative to center pixel to convert from window
        # graphics space to standard X/Y coordinate space
        win_pts = np.asarray(win_pts, dtype=np.float)
        has_z = (win_pts.shape[-1] > 2)

        ctr_pt = list(self.viewer.get_center())
        if has_z:
            ctr_pt.append(0.0)

        mpy_pt = [1.0, -1.0]
        if has_z:
            mpy_pt.append(1.0)

        # off_x = win_x - ctr_x
        #       = win_x + -ctr_x
        # off_y = ctr_y - win_y
        #       = -win_y + ctr_y
        ctr_pt[0] = -ctr_pt[0]
        off_pts = np.add(np.multiply(win_pts, mpy_pt), ctr_pt)

        return off_pts


class CartesianNativeTransform(BaseTransform):
    """
    A transform from cartesian coordinates to the native pixel coordinates
    of a viewer.
    """

    def __init__(self, viewer, as_int=True):
        super(CartesianNativeTransform, self).__init__()
        self.viewer = viewer
        self.as_int = as_int

    def to_(self, off_pts):
        # add center pixel to convert from X/Y coordinate space to
        # back end graphics space
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        ctr_pt = list(self.viewer.get_center())
        if has_z:
            ctr_pt.append(0.0)

        if self.viewer.origin_upper:
            mpy_pt = [1.0, -1.0]
        else:
            mpy_pt = [1.0, 1.0]

        if has_z:
            mpy_pt.append(1.0)

        win_pts = np.add(np.multiply(off_pts, mpy_pt), ctr_pt)

        # round to pixel units, if asked
        # round to pixel units, if asked
        if self.as_int:
            win_pts = np.rint(win_pts).astype(np.int, copy=False)

        return win_pts

    def from_(self, win_pts):
        """Reverse of :meth:`to_`."""
        # make relative to center pixel to convert from back end
        # graphics space to standard X/Y coordinate space
        win_pts = np.asarray(win_pts, dtype=np.float)
        has_z = (win_pts.shape[-1] > 2)

        ctr_pt = list(self.viewer.get_center())
        if has_z:
            ctr_pt.append(0.0)

        ctr_pt[0] = -ctr_pt[0]
        if self.viewer.origin_upper:
            mpy_pt = [1.0, -1.0]
        else:
            ctr_pt[1] = -ctr_pt[1]
            mpy_pt = [1.0, 1.0]

        if has_z:
            mpy_pt.append(1.0)

        off_pts = np.add(np.multiply(win_pts, mpy_pt), ctr_pt)

        return off_pts


class RotationTransform(BaseTransform):
    """
    A transform in cartesian coordinates based on the flip/swap setting and
    rotation setting of a viewer.
    """

    def __init__(self, viewer):
        super(RotationTransform, self).__init__()
        self.viewer = viewer

    def to_(self, off_pts):
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        t_ = self.viewer.t_

        # flip
        flip_pt = [1.0, 1.0]
        if t_['flip_x']:
            flip_pt[0] = -1.0
        if t_['flip_y']:
            flip_pt[1] = -1.0
        if has_z:
            # no flip_z at the moment
            flip_pt.append(1.0)

        off_pts = np.multiply(off_pts, flip_pt)

        # swap
        if t_['swap_xy']:
            p = list(off_pts.T)
            off_pts = np.asarray([p[1], p[0]] + list(p[2:])).T

        # rotate
        if t_['rot_deg'] != 0:
            thetas = [t_['rot_deg']]
            offset = [0.0, 0.0]
            if has_z:
                offset.append(0.0)
            off_pts = trcalc.rotate_coord(off_pts, thetas, offset)

        return off_pts

    def from_(self, off_pts):
        """Reverse of :meth:`to_`."""
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        t_ = self.viewer.t_

        # rotate
        if t_['rot_deg'] != 0:
            thetas = [- t_['rot_deg']]
            offset = [0.0, 0.0]
            if has_z:
                offset.append(0.0)
            off_pts = trcalc.rotate_coord(off_pts, thetas, offset)

        # swap
        if t_['swap_xy']:
            p = list(off_pts.T)
            off_pts = np.asarray([p[1], p[0]] + list(p[2:])).T

        # flip
        flip_pt = [1.0, 1.0]
        if t_['flip_x']:
            flip_pt[0] = -1.0
        if t_['flip_y']:
            flip_pt[1] = -1.0
        if has_z:
            # no flip_z at the moment
            flip_pt.append(1.0)

        off_pts = np.multiply(off_pts, flip_pt)

        return off_pts


class ScaleTransform(BaseTransform):
    """
    A transform in cartesian coordinates based on the scale of a viewer.
    """

    def __init__(self, viewer):
        super(ScaleTransform, self).__init__()
        self.viewer = viewer

    def to_(self, off_pts):
        """Reverse of :meth:`from_`."""
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        # scale according to current settings
        scale_pt = [self.viewer._org_scale_x, self.viewer._org_scale_y]
        if has_z:
            scale_pt.append(self.viewer._org_scale_z)

        off_pts = np.multiply(off_pts, scale_pt)
        return off_pts

    def from_(self, off_pts):
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        scale_pt = [1.0 / self.viewer._org_scale_x,
                    1.0 / self.viewer._org_scale_y]
        if has_z:
            scale_pt.append(1.0 / self.viewer._org_scale_z)

        # Reverse scaling
        off_pts = np.multiply(off_pts, scale_pt)
        return off_pts


class DataCartesianTransform(BaseTransform):
    """
    A transform from data coordinates to cartesian coordinates based on
    a viewer's pan position.
    """

    def __init__(self, viewer, use_center=True):
        super(DataCartesianTransform, self).__init__()
        self.viewer = viewer
        # If use_center is True, then the coordinates are mapped such that the
        # pixel is centered on the square when the image is zoomed in past
        # 1X. This is the specification of the FITS image standard,
        # that the pixel is centered on the integer row/column.
        self.use_center = use_center

    def to_(self, data_pts):
        """Reverse of :meth:`from_`."""
        data_pts = np.asarray(data_pts, dtype=np.float)
        has_z = (data_pts.shape[-1] > 2)

        if self.use_center:
            data_pts = data_pts - self.viewer.data_off

        # subtract data indexes at center reference pixel
        ref_pt = [self.viewer._org_x, self.viewer._org_y]
        if has_z:
            ref_pt.append(self.viewer._org_z)

        off_pts = np.subtract(data_pts, ref_pt)
        return off_pts

    def from_(self, off_pts):
        off_pts = np.asarray(off_pts, dtype=np.float)
        has_z = (off_pts.shape[-1] > 2)

        # Add data index at center to offset
        # subtract data indexes at center reference pixel
        ref_pt = [self.viewer._org_x, self.viewer._org_y]
        if has_z:
            ref_pt.append(self.viewer._org_z)

        data_pts = np.add(off_pts, ref_pt)

        if self.use_center:
            data_pts = data_pts + self.viewer.data_off

        return data_pts


class OffsetDataTransform(BaseTransform):
    """
    A transform whose coordinate space is offsets from a point in
    data space.
    """

    def __init__(self, pt):
        super(OffsetDataTransform, self).__init__()
        self.pt = pt

    def to_(self, delta_pts):
        delta_x, delta_y = np.asarray(delta_pts, dtype=np.float).T
        ref_x, ref_y = self.pt[:2]
        res_x, res_y = ref_x + delta_x, ref_y + delta_y
        return np.asarray((res_x, res_y)).T

    def from_(self, data_pts):
        data_x, data_y = np.asarray(data_pts, dtype=np.float).T
        ref_x, ref_y = self.pt[:2]
        res_x, res_y = data_x - ref_x, data_y - ref_y
        return np.asarray((res_x, res_y)).T


class WCSDataTransform(BaseTransform):
    """
    A transform whose coordinate space is based on the WCS of the primary
    image loaded in a viewer.
    """

    def __init__(self, viewer):
        super(WCSDataTransform, self).__init__()
        self.viewer = viewer

    def to_(self, wcs_pts):
        wcs_pts = np.asarray(wcs_pts)

        # hack to work around passing singleton pt vs. array of pts
        unpack = False
        if len(wcs_pts.shape) < 2:
            # passed a single coordinate
            wcs_pts = np.asarray([wcs_pts])
            unpack = True

        image = self.viewer.get_image()
        if image is None:
            raise TransformError("No image, no WCS")
        wcs = image.wcs
        if wcs is None:
            raise TransformError("No valid WCS found in image")

        naxispath = image.naxispath

        res = wcs.wcspt_to_datapt(wcs_pts, naxispath=naxispath)
        if unpack:
            return res[0]
        return res

    def from_(self, data_pts):
        data_pts = np.asarray(data_pts)

        # hack to work around passing singleton pt vs. array of pts
        unpack = False
        if len(data_pts.shape) < 2:
            # passed a single coordinate
            data_pts = np.asarray([data_pts])
            unpack = True

        image = self.viewer.get_image()
        if image is None:
            raise TransformError("No image, no WCS")
        wcs = image.wcs
        if wcs is None:
            raise TransformError("No valid WCS found in image")

        naxispath = image.naxispath

        res = wcs.datapt_to_wcspt(data_pts, naxispath=naxispath)
        if unpack:
            return res[0]
        return res


def get_catalog():
    """Returns a catalog of available transforms.  These are used to
    build chains for rendering with different back ends.
    """
    tforms = {}
    for name, value in list(globals().items()):
        if name.endswith('Transform'):
            tforms[name] = value

    return Bunch.Bunch(tforms, caseless=True)

#END
