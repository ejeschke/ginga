#
# coordmap.py -- coordinate mappings.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import trcalc
from ginga.util import wcs
from ginga.util.six.moves import map

__all__ = ['CanvasMapper', 'CartesianMapper', 'DataMapper', 'OffsetMapper',
           'WCSMapper']

class CoordMapError(Exception):
    pass


class BaseMapper(object):
    """Base class for coordinate mapper objects."""
    def __init__(self):
        super(BaseMapper, self).__init__()

    def to_canvas(self, canvas_x, canvas_y):
        raise CoordMapError("this method is deprecated")

    def to_data(self, canvas_x, canvas_y):
        raise CoordMapError("subclass should override this method")

    def data_to(self, data_x, data_y):
        raise CoordMapError("subclass should override this method")

    def offset_pt(self, pt, xoff, yoff):
        """
        Offset a point specified by `pt`, by the offsets (`xoff`, `yoff`).
        Coordinates are assumed to be in the space defined by this mapper.
        """
        raise CoordMapError("subclass should override this method")

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        """
        Rotate a point specified by (`x`, `y`) by the angle `theta` (in degrees)
        around the point indicated by (`xoff`, `yoff`).
        Coordinates are assumed to be in the space defined by this mapper.
        """
        raise CoordMapError("subclass should override this method")

class CanvasMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer's canvas in
    canvas coordinates.
    """
    def __init__(self, viewer):
        super(CanvasMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, canvas_x, canvas_y, viewer=None):
        if viewer is None:
            viewer = self.viewer

        canvas_x, canvas_y = viewer.tform['canvas_to_window'].from_(canvas_x,
                                                                    canvas_y)
        # flip Y axis for certain backends
        return viewer.tform['data_to_window'].from_(canvas_x, canvas_y)

    def data_to(self, data_x, data_y, viewer=None):
        if viewer is None:
            viewer = self.viewer

        canvas_x, canvas_y = viewer.tform['data_to_window'].to_(data_x,
                                                                data_y)
        # flip Y axis for certain backends
        return viewer.tform['canvas_to_window'].to_(canvas_x, canvas_y)

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        # TODO?  Not sure if it is needed with this mapper type
        return x, y


class CartesianMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer's canvas
    in Cartesian coordinates that do not scale (unlike DataMapper).
    """
    def __init__(self, viewer):
        super(CartesianMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, crt_x, crt_y, viewer=None):
        if viewer is None:
            viewer = self.viewer
        return viewer.tform['data_to_cartesian'].from_(crt_x, crt_y)

    def data_to(self, data_x, data_y, viewer=None):
        if viewer is None:
            viewer = self.viewer
        return viewer.tform['data_to_cartesian'].to_(data_x, data_y)

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        return trcalc.rotate_pt(x, y, theta, xoff=xoff, yoff=yoff)


class DataMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer's canvas
    in data coordinates.
    """
    def __init__(self, viewer):
        super(DataMapper, self).__init__()
        self.viewer = viewer

    def to_data(self, data_x, data_y, viewer=None):
        return data_x, data_y

    def data_to(self, data_x, data_y, viewer=None):
        return data_x, data_y

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        return trcalc.rotate_pt(x, y, theta, xoff=xoff, yoff=yoff)


class OffsetMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer's canvas
    in data coordinates that are offsets relative to some other
    reference object.
    """
    def __init__(self, viewer, refobj):
        super(OffsetMapper, self).__init__()
        # TODO: provide a keyword arg to specify which point in the obj
        self.viewer = viewer
        self.refobj = refobj

    def calc_offsets(self, points):
        ref_x, ref_y = self.refobj.get_reference_pt()
        #return map(lambda x, y: x - ref_x, y - ref_y, points)
        def _cvt(pt):
            x, y = pt
            return x - ref_x, y - ref_y
        return map(_cvt, points)

    def to_data(self, delta_x, delta_y, viewer=None):
        if viewer is None:
            viewer = self.viewer
        ref_x, ref_y = self.refobj.get_reference_pt()
        data_x, data_y = self.refobj.crdmap.to_data(ref_x, ref_y, viewer=viewer)
        return data_x + delta_x, data_y + delta_y

    def data_to(self, data_x, data_y, viewer=None):
        ref_x, ref_y = self.refobj.get_reference_pt()
        return data_x - ref_x, data_y - ref_y

    def offset_pt(self, pt, xoff, yoff):
        # A no-op because this object's points are always considered
        # relative to the reference object
        return pt

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        # TODO?  Not sure if it is needed with this mapper type
        return x, y


class WCSMapper(BaseMapper):
    """A coordinate mapper that maps to the viewer's canvas
    in WCS coordinates.
    """

    def __init__(self, viewer, data_mapper):
        super(WCSMapper, self).__init__()
        self.viewer = viewer
        self.data_mapper = data_mapper

    def to_data(self, lon, lat, viewer=None):
        if viewer is None:
            viewer = self.viewer
        return viewer.tform['wcs_to_data'].to_(lon, lat)

    def data_to(self, data_x, data_y, viewer=None):
        if viewer is None:
            viewer = self.viewer
        return viewer.tform['wcs_to_data'].from_(data_x, data_y)

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return wcs.add_offset_radec(x, y, xoff, yoff)

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        # TODO: rotate in WCS space?
        # rotate in data space
        xoff, yoff = self.to_data(xoff, yoff)
        data_x, data_y = self.to_data(x, y)

        rot_x, rot_y = trcalc.rotate_pt(data_x, data_y, theta,
                                        xoff=xoff, yoff=yoff)

        x, y = self.data_to(rot_x, rot_y)
        return x, y


#END
