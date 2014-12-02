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
    def __init__(self, viewer):
        # record the viewer just in case
        self.viewer = viewer
        
    def mapcoords(self, canvas_x, canvas_y):
        return (canvas_x, canvas_y)

    def offset(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff
    
    
class DataMapper(object):
    """A coordinate mapper that maps to the viewer's default
    data mapping.
    """
    def __init__(self, viewer):
        self.viewer = viewer
        
    def mapcoords(self, data_x, data_y):
        return self.viewer.canvascoords(data_x, data_y)

    def offset(self, pt, xoff, yoff):
        x, y = pt
        return x + xoff, y + yoff

    
class OffsetMapper(object):
    """A coordinate mapper that maps relative to some other
    reference object.
    """
    def __init__(self, viewer, refobj):
        self.viewer = viewer
        self.refobj = refobj
        
    def mapcoords(self, delta_x, delta_y):
        data_x, data_y = self.refobj.get_reference_pt()
        return self.viewer.canvascoords(data_x + delta_x,
                                        data_y + delta_y)

    def offset(self, pt, xoff, yoff):
        return pt
    
    
class WCSMapper(DataMapper):

    def mapcoords(self, ra, dec):
        image = self.viewer.get_image()
        data_x, data_y = image.radectopix(ra, dec)
        return super(WCSMapper, self).mapcoords(data_x, data_y)
    
    
#END
