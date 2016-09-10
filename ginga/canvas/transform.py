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

    def to_(self, x, y):
        return self.tform2.to_(*self.tform1.to_(x, y))

    def from_(self, tx, ty):
        return self.tform1.from_(*self.tform2.from_(tx, ty))


class CanvasWindowTransform(BaseTransform):
    """
    A transform from a possibly Y-flipped pixel space to a typical
    window pixel coordinate space with the lower left at (0, 0).
    """

    def __init__(self, viewer):
        super(CanvasWindowTransform, self).__init__()
        self.viewer = viewer

    def to_(self, cvs_x, cvs_y):
        if self.viewer._originUpper:
            return (cvs_x, cvs_y)

        # invert Y coord for backends that have the origin in the lower left
        win_wd, win_ht = self.viewer.get_window_size()
        win_x, win_y = cvs_x, win_ht - cvs_y
        return (win_x, win_y)

    def from_(self, win_x, win_y):
        return self.to_(win_x, win_y)


class CartesianWindowTransform(BaseTransform):
    """
    A transform from non-scaled cartesian coordinates to the flipped,
    swapped and rotated window pixel coordinates of the back end.
    """

    def __init__(self, viewer):
        super(CartesianWindowTransform, self).__init__()
        self.viewer = viewer

    def to_(self, off_x, off_y, asint=True):
        """Convert non-scaled cartesian offset to window coordinates.

        Parameters
        ----------
        off_x, off_y : float or ndarray
            Non-scaled cartesian offsets.

        asint : bool
            Force output coordinates to be integers.

        Returns
        -------
        coord : tuple
            Offset in window coordinates in the form of ``(x, y)``.

        """
        t_ = self.viewer.t_
        if t_['flip_x']:
            off_x = - off_x
        if t_['flip_y']:
            off_y = - off_y
        if t_['swap_xy']:
            off_x, off_y = off_y, off_x

        if t_['rot_deg'] != 0:
            off_x, off_y = trcalc.rotate_pt(off_x, off_y, t_['rot_deg'])

        # add center pixel to convert from X/Y coordinate space to
        # canvas graphics space
        ctr_x, ctr_y = self.viewer.get_center()
        win_x = off_x + ctr_x
        if self.viewer._originUpper:
            win_y = ctr_y - off_y
        else:
            win_y = off_y + ctr_y

        # round to pixel units, if asked
        if asint:
            win_x = np.rint(win_x).astype(np.int)
            win_y = np.rint(win_y).astype(np.int)

        return (win_x, win_y)

    def from_(self, win_x, win_y):
        """Reverse of :meth:`to_`."""
        # make relative to center pixel to convert from canvas
        # graphics space to standard X/Y coordinate space
        ctr_x, ctr_y = self.viewer.get_center()
        off_x = win_x - ctr_x
        if self.viewer._originUpper:
            off_y = ctr_y - win_y
        else:
            off_y = win_y - ctr_y

        t_ = self.viewer.t_
        if t_['rot_deg'] != 0:
            off_x, off_y = trcalc.rotate_pt(off_x, off_y, -t_['rot_deg'])

        if t_['swap_xy']:
            off_x, off_y = off_y, off_x
        if t_['flip_y']:
            off_y = - off_y
        if t_['flip_x']:
            off_x = - off_x

        return (off_x, off_y)


class DataCartesianTransform(BaseTransform):
    """
    A transform from the scaled data space of a viewer to non-scaled
    cartesian coordinates.
    """

    def __init__(self, viewer):
        super(DataCartesianTransform, self).__init__()
        self.viewer = viewer

    def to_(self, data_x, data_y, center=True):
        """Reverse of :meth:`from_`."""
        if center:
            data_x -= self.viewer.data_off
            data_y -= self.viewer.data_off
        # subtract data indexes at center reference pixel
        off_x = data_x - self.viewer._org_x
        off_y = data_y - self.viewer._org_y

        # scale according to current settings
        off_x *= self.viewer._org_scale_x
        off_y *= self.viewer._org_scale_y

        return (off_x, off_y)

    def from_(self, off_x, off_y, center=True):
        """Get the closest coordinates in the data array to those
        in cartesian fixed (non-scaled) canvas coordinates.

        Parameters
        ----------
        off_x, off_y : float or ndarray
            Cartesian canvas coordinates.

        center : bool
            If `True`, then the coordinates are mapped such that the
            pixel is centered on the square when the image is zoomed in past
            1X. This is the specification of the FITS image standard,
            that the pixel is centered on the integer row/column.

        Returns
        -------
        coord : tuple
            Data coordinates in the form of ``(x, y)``.

        """
        # Reverse scaling
        off_x = off_x * (1.0 / self.viewer._org_scale_x)
        off_y = off_y * (1.0 / self.viewer._org_scale_y)

        # Add data index at (_ctr_x, _ctr_y) to offset
        data_x = self.viewer._org_x + off_x
        data_y = self.viewer._org_y + off_y
        if center:
            data_x += self.viewer.data_off
            data_y += self.viewer.data_off

        return (data_x, data_y)


class OffsetDataTransform(BaseTransform):
    """
    A transform whose coordinate space is offsets from a point in
    data space.
    """

    def __init__(self, pt):
        super(OffsetDataTransform, self).__init__()
        self.pt = pt

    def to_(self, delta_x, delta_y):
        ref_x, ref_y = self.pt[:2]
        return (ref_x + delta_x, ref_y + delta_y)

    def from_(self, data_x, data_y):
        ref_x, ref_y = self.pt[:2]
        return (data_x - ref_x, data_y - ref_y)


class WCSDataTransform(BaseTransform):
    """
    A transform whose coordinate space is based on the WCS of the primary
    image loaded in a viewer.
    """

    def __init__(self, viewer):
        super(WCSDataTransform, self).__init__()
        self.viewer = viewer

    def to_(self, lon, lat):
        image = self.viewer.get_image()
        if image is None:
            raise TransformError("No image, no WCS")

        data_x, data_y = image.radectopix(lon, lat)
        return (data_x, data_y)

    def from_(self, data_x, data_y):
        image = self.viewer.get_image()
        if image is None:
            raise TransformError("No image, no WCS")

        lon, lat = image.pixtoradec(data_x, data_y)
        return (lon, lat)


#END
