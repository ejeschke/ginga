#
# coordmap.py -- coordinate mappings.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc
from ginga.util import wcs

__all__ = ['NativeMapper', 'WindowMapper', 'PercentageMapper',
           'CartesianMapper', 'DataMapper', 'OffsetMapper', 'WCSMapper']


class CoordMapError(Exception):
    pass


class BaseMapper(object):
    """Base class for coordinate mapper objects."""
    def __init__(self):
        super(BaseMapper, self).__init__()

    def to_canvas(self, canvas_x, canvas_y):
        raise CoordMapError("this method is deprecated")

    def to_data(self, pts):
        raise CoordMapError("subclass should override this method")

    def data_to(self, pts):
        raise CoordMapError("subclass should override this method")

    def offset_pt(self, pts, offset):
        """
        Offset a point specified by `pt`, by the offsets `offset`.
        Coordinates are assumed to be in the space defined by this mapper.
        """
        raise CoordMapError("subclass should override this method")

    def rotate_pt(self, pts, theta, offset=None):
        """
        Rotate a point specified by `pt` by the angle `theta` (in degrees)
        around the point indicated by `offset`.
        Coordinates are assumed to be in the space defined by this mapper.
        """
        raise CoordMapError("subclass should override this method")


class NativeMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer's canvas in
    the viewer's canvas coordinates.
    """
    def __init__(self, viewer):
        super(NativeMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, cvs_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer

        cvs_arr = np.asarray(cvs_pts)
        return viewer.tform['data_to_native'].from_(cvs_arr)

    def data_to(self, data_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer

        data_arr = np.asarray(data_pts)
        return viewer.tform['data_to_native'].to_(data_arr)

    def offset_pt(self, pts, offset):
        return np.add(pts, offset)

    def rotate_pt(self, pts, theta, offset):
        # TODO?  Not sure if it is needed with this mapper type
        return pts


class WindowMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer in 'window' coordinates.
    """
    def __init__(self, viewer):
        super(WindowMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, cvs_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer

        cvs_arr = np.asarray(cvs_pts)
        return viewer.tform['data_to_window'].from_(cvs_arr)

    def data_to(self, data_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer

        data_arr = np.asarray(data_pts)
        return viewer.tform['data_to_window'].to_(data_arr)

    def offset_pt(self, pts, offset):
        return np.add(pts, offset)

    def rotate_pt(self, pts, theta, offset):
        # TODO?  Not sure if it is needed with this mapper type
        return pts


class PercentageMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer in 'percentage' coordinates.
    """
    def __init__(self, viewer):
        super(PercentageMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, pct_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer

        pct_arr = np.asarray(pct_pts)
        return viewer.tform['data_to_percentage'].from_(pct_arr)

    def data_to(self, data_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer

        data_arr = np.asarray(data_pts)
        return viewer.tform['data_to_percentage'].to_(data_arr)

    def offset_pt(self, pts, offset):
        return np.add(pts, offset)

    def rotate_pt(self, pts, theta, offset):
        # TODO?  Not sure if it is needed with this mapper type
        return pts


class CartesianMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer in Cartesian
    coordinates that do not scale (unlike DataMapper).
    """
    def __init__(self, viewer):
        super(CartesianMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, crt_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer
        crt_arr = np.asarray(crt_pts)
        return viewer.tform['data_to_cartesian'].from_(crt_arr)

    def data_to(self, data_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer
        data_arr = np.asarray(data_pts)
        return viewer.tform['data_to_cartesian'].to_(data_arr)

    def offset_pt(self, pts, offset):
        return np.add(pts, offset)

    def rotate_pt(self, pts, theta, offset):
        x, y = np.asarray(pts).T
        xoff, yoff = np.transpose(offset)
        rot_x, rot_y = trcalc.rotate_pt(x, y, theta, xoff=xoff, yoff=yoff)
        return np.asarray((rot_x, rot_y)).T


class DataMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer in data coordinates.
    """
    def __init__(self, viewer):
        super(DataMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, data_pts, viewer=None):
        return data_pts

    def data_to(self, data_pts, viewer=None):
        return data_pts

    def offset_pt(self, pts, offset):
        return np.add(pts, offset)

    def rotate_pt(self, pts, theta, offset):
        x, y = np.asarray(pts).T
        xoff, yoff = np.transpose(offset)
        rot_x, rot_y = trcalc.rotate_pt(x, y, theta, xoff=xoff, yoff=yoff)
        return np.asarray((rot_x, rot_y)).T


class OffsetMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer in data coordinates
    that are offsets relative to some other reference object.
    """
    def __init__(self, viewer, refobj):
        super(OffsetMapper, self).__init__()
        # TODO: provide a keyword arg to specify which point in the obj
        self.viewer = viewer
        self.refobj = refobj

    def calc_offsets(self, pts):
        ref_pt = self.refobj.get_reference_pt()
        return np.subtract(pts, ref_pt)

    def to_data(self, delta_pt, viewer=None):
        if viewer is None:
            viewer = self.viewer
        ref_pt = self.refobj.get_reference_pt()
        data_pt = self.refobj.crdmap.to_data(ref_pt, viewer=viewer)
        return np.add(data_pt, delta_pt)

    def data_to(self, data_pts, viewer=None):
        ref_pt = self.refobj.get_reference_pt()
        return np.subtract(data_pts, ref_pt)

    def offset_pt(self, pts, offset):
        # A no-op because this object's points are always considered
        # relative to the reference object
        return pts

    def rotate_pt(self, pts, theta, offset):
        # TODO?  Not sure if it is needed with this mapper type
        return pts


class WCSMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer in WCS coordinates.
    """

    def __init__(self, viewer):
        super(WCSMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, wcs_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer
        return viewer.tform['wcs_to_data'].to_(wcs_pts)

    def data_to(self, data_pts, viewer=None):
        if viewer is None:
            viewer = self.viewer
        data_arr = np.asarray(data_pts)
        return viewer.tform['wcs_to_data'].from_(data_arr)

    def offset_pt(self, pts, offset):
        x, y = np.transpose(pts)
        #xoff, yoff = np.transpose(offset)
        xoff, yoff = offset
        res_arr = wcs.add_offset_radec(x, y, xoff, yoff)
        return np.transpose(res_arr)

    def rotate_pt(self, pts, theta, offset):
        # TODO: rotate in WCS space?
        # rotate in data space
        data_off = self.to_data(offset)
        data_pts = self.to_data(pts)

        xoff, yoff = np.transpose(data_off)
        data_x, data_y = data_pts.T
        data_rot = trcalc.rotate_pt(data_x, data_y, theta,
                                    xoff=xoff, yoff=yoff)

        return self.data_to(data_rot.T)


# END
