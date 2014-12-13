#
# coormap.py -- coordinate mappings to canvas.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

class CanvasMapper(object):
    """A coordinate mapper that maps to the viewer's canvas in
    canvas coordinates.
    """
    def __init__(self, viewer):
        # record the viewer just in case
        self.viewer = viewer
        
    def to_canvas(self, canvas_x, canvas_y):
        return (canvas_x, canvas_y)

    def offset(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff
    
    
class DataMapper(object):
    """A coordinate mapper that maps to the viewer's canvas
    in data coordinates.
    """
    def __init__(self, viewer):
        self.viewer = viewer
        
    def to_canvas(self, data_x, data_y):
        return self.viewer.canvascoords(data_x, data_y)

    def offset(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    
class OffsetMapper(object):
    """A coordinate mapper that maps to the viewer's canvas
    in data coordinates that are offsets relative to some other
    reference object.
    """
    def __init__(self, viewer, refobj):
        # TODO: provide a keyword arg to specify which point in the obj
        self.viewer = viewer
        self.refobj = refobj
        
    def to_canvas(self, delta_x, delta_y):
        data_x, data_y = self.refobj.get_reference_pt()
        return self.viewer.canvascoords(data_x + delta_x,
                                        data_y + delta_y)

    def offset(self, pt, xoff, yoff):
        return pt
    
    
class WCSMapper(DataMapper):
    """A coordinate mapper that maps to the viewer's canvas
    in WCS coordinates.
    """

    def to_canvas(self, lon, lat):
        image = self.viewer.get_image()

        # convert to data coords
        data_x, data_y = image.radectopix(lon, lat)

        return super(WCSMapper, self).to_canvas(data_x, data_y)
    
    
#END
