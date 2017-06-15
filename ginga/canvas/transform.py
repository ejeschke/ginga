#
# transform.py -- coordinate transforms for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc

__all__ = ['TransformError', 'BaseTransform', 'ComposedTransform',
           'CanvasWindowTransform', 'CartesianWindowTransform',
           'RotationTransform', 'ScaleTransform',
           'DataCartesianTransform', 'OffsetDataTransform',
           'WCSDataTransform',
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


class CanvasWindowTransform(BaseTransform):
    """
    A transform from a possibly Y-flipped pixel space to a typical
    window pixel coordinate space with the lower left at (0, 0).
    """

    def __init__(self, viewer):
        super(CanvasWindowTransform, self).__init__()
        self.viewer = viewer

    def to_(self, cvs_pts):
        if self.viewer.origin_upper:
            return cvs_pts

        # invert Y coord for backends that have the origin in the lower left
        win_wd, win_ht = self.viewer.get_window_size()
        cvs_x, cvs_y = np.asarray(cvs_pts).T

        win_x, win_y = cvs_x, win_ht - cvs_y
        return np.asarray((win_x, win_y)).T

    def from_(self, win_pts):
        return self.to_(win_pts)


class CartesianWindowTransform(BaseTransform):
    """
    A transform from cartesian coordinates to the window pixel coordinates
    of a viewer.
    """

    def __init__(self, viewer, as_int=True):
        super(CartesianWindowTransform, self).__init__()
        self.viewer = viewer
        self.as_int = as_int

    def to_(self, off_pts):
        # add center pixel to convert from X/Y coordinate space to
        # canvas graphics space
        ctr_x, ctr_y = self.viewer.get_center()
        off_x, off_y = np.asarray(off_pts, dtype=np.float).T

        win_x = off_x + ctr_x
        if self.viewer.origin_upper:
            win_y = ctr_y - off_y
        else:
            win_y = off_y + ctr_y

        # round to pixel units, if asked
        if self.as_int:
            win_x = np.rint(win_x).astype(np.int)
            win_y = np.rint(win_y).astype(np.int)

        return np.asarray((win_x, win_y)).T

    def from_(self, win_pts):
        """Reverse of :meth:`to_`."""
        # make relative to center pixel to convert from canvas
        # graphics space to standard X/Y coordinate space
        ctr_x, ctr_y = self.viewer.get_center()
        win_x, win_y = np.asarray(win_pts).T

        off_x = win_x - ctr_x
        if self.viewer.origin_upper:
            off_y = ctr_y - win_y
        else:
            off_y = win_y - ctr_y

        return np.asarray((off_x, off_y)).T


class RotationTransform(BaseTransform):
    """
    A transform in cartesian coordinates based on the flip/swap setting and
    rotation setting of a viewer.
    """

    def __init__(self, viewer):
        super(RotationTransform, self).__init__()
        self.viewer = viewer

    def to_(self, off_pts):
        off_x, off_y = np.asarray(off_pts, dtype=np.float).T

        t_ = self.viewer.t_
        if t_['flip_x']:
            off_x = - off_x
        if t_['flip_y']:
            off_y = - off_y
        if t_['swap_xy']:
            off_x, off_y = off_y, off_x

        if t_['rot_deg'] != 0:
            off_x, off_y = trcalc.rotate_pt(off_x, off_y, t_['rot_deg'])

        return np.asarray((off_x, off_y)).T

    def from_(self, off_pts):
        """Reverse of :meth:`to_`."""
        off_x, off_y = np.asarray(off_pts, dtype=np.float).T

        t_ = self.viewer.t_
        if t_['rot_deg'] != 0:
            off_x, off_y = trcalc.rotate_pt(off_x, off_y, -t_['rot_deg'])

        if t_['swap_xy']:
            off_x, off_y = off_y, off_x
        if t_['flip_y']:
            off_y = - off_y
        if t_['flip_x']:
            off_x = - off_x

        return np.asarray((off_x, off_y)).T


class ScaleTransform(BaseTransform):
    """
    A transform in cartesian coordinates based on the scale of a viewer.
    """

    def __init__(self, viewer):
        super(ScaleTransform, self).__init__()
        self.viewer = viewer

    def to_(self, off_pts):
        """Reverse of :meth:`from_`."""
        off_x, off_y = np.asarray(off_pts, dtype=np.float).T

        # scale according to current settings
        off_x = off_x * self.viewer._org_scale_x
        off_y = off_y * self.viewer._org_scale_y

        return np.asarray((off_x, off_y)).T

    def from_(self, off_pts):
        off_x, off_y = np.asarray(off_pts, dtype=np.float).T

        # Reverse scaling
        off_x = off_x * (1.0 / self.viewer._org_scale_x)
        off_y = off_y * (1.0 / self.viewer._org_scale_y)

        return np.asarray((off_x, off_y)).T


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
        data_x, data_y = np.asarray(data_pts, dtype=np.float).T

        if self.use_center:
            data_x = data_x - self.viewer.data_off
            data_y = data_y - self.viewer.data_off

        # subtract data indexes at center reference pixel
        off_x = data_x - self.viewer._org_x
        off_y = data_y - self.viewer._org_y

        return np.asarray((off_x, off_y)).T

    def from_(self, off_pts):
        off_x, off_y = np.asarray(off_pts, dtype=np.float).T

        # Add data index at center to offset
        data_x = self.viewer._org_x + off_x
        data_y = self.viewer._org_y + off_y

        if self.use_center:
            data_x = data_x + self.viewer.data_off
            data_y = data_y + self.viewer.data_off

        return np.asarray((data_x, data_y)).T


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
        image = self.viewer.get_image()
        if image is None:
            raise TransformError("No image, no WCS")
        wcs = image.wcs
        if wcs is None:
            raise TransformError("No valid WCS found in image")

        return wcs.wcspt_to_datapt(wcs_pts)

    def from_(self, data_pts):
        data_pts = np.asarray(data_pts)
        image = self.viewer.get_image()
        if image is None:
            raise TransformError("No image, no WCS")
        wcs = image.wcs
        if wcs is None:
            raise TransformError("No valid WCS found in image")

        return wcs.datapt_to_wcspt(data_pts)


#END
