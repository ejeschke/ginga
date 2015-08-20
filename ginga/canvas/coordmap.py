#
# coormap.py -- coordinate mappings.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import trcalc
from ginga.util import wcs
from ginga.util.six.moves import map

class CanvasMapper(object):
    """A coordinate mapper that maps to the viewer's canvas in
    canvas coordinates.
    """
    def __init__(self, viewer):
        # record the viewer just in case
        self.viewer = viewer

    def to_canvas(self, canvas_x, canvas_y):
        return (canvas_x, canvas_y)

    def to_data(self, canvas_x, canvas_y):
        return self.viewer.get_data_xy(canvas_x, canvas_y)

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        # TODO?  Not sure if it is needed with this mapper type
        return x, y


class DataMapper(object):
    """A coordinate mapper that maps to the viewer's canvas
    in data coordinates.
    """
    def __init__(self, viewer):
        self.viewer = viewer

    def to_canvas(self, data_x, data_y):
        return self.viewer.canvascoords(data_x, data_y)

    def to_data(self, data_x, data_y):
        return data_x, data_y

    def data_to(self, data_x, data_y):
        return data_x, data_y

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        return trcalc.rotate_pt(x, y, theta, xoff=xoff, yoff=yoff)

class OffsetMapper(object):
    """A coordinate mapper that maps to the viewer's canvas
    in data coordinates that are offsets relative to some other
    reference object.
    """
    def __init__(self, viewer, refobj):
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

    def to_canvas(self, delta_x, delta_y):
        data_x, data_y = self.to_data(delta_x, delta_y)
        return self.viewer.canvascoords(data_x, data_y)

    def to_data(self, delta_x, delta_y):
        ref_x, ref_y = self.refobj.get_reference_pt()
        data_x, data_y = self.refobj.crdmap.to_data(ref_x, ref_y)
        return data_x + delta_x, data_y + delta_y

    ## def data_to(self, data_x, data_y):
    ##     ref_x, ref_y = self.refobj.get_reference_pt()
    ##     return data_x - ref_data_x, data_y - ref_data_y

    def offset_pt(self, pt, xoff, yoff):
        # A no-op because this object's points are always considered
        # relative to the reference object
        return pt

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        # TODO?  Not sure if it is needed with this mapper type
        return x, y

class WCSMapper(DataMapper):
    """A coordinate mapper that maps to the viewer's canvas
    in WCS coordinates.
    """

    def to_canvas(self, lon, lat):
        data_x, data_y = self.to_data(lon, lat)
        return super(WCSMapper, self).to_canvas(data_x, data_y)

    def to_data(self, lon, lat):
        image = self.viewer.get_image()
        data_x, data_y = image.radectopix(lon, lat)
        return data_x, data_y

    def data_to(self, data_x, data_y):
        image = self.viewer.get_image()
        lon, lat = image.pixtoradec(data_x, data_y)
        return lon, lat

    def offset_pt(self, pt, xoff, yoff):
        x, y = pt
        return wcs.add_offset_radec(x, y, xoff, yoff)

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        # TODO: optomize by rotating in WCS space
        x, y = self.to_data(x, y)
        xoff, yoff = self.to_data(xoff, yoff)

        x, y = super(WCSMapper, self).rotate_pt(x, y, theta,
                                                xoff=xoff, yoff=yoff)
        x, y = self.data_to(x, y)
        return x, y


#END
