#
# ImageViewCanvas.py -- base classes for ImageViewCanvas{Toolkit}.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy

from ginga.misc import Callback, Bunch
from ginga.misc.ParamSet import Param
from ginga.util import wcs
from ginga import trcalc, Mixins, colors
from ginga.util.six.moves import map, filter

from ginga.canvas.CompoundMixin import CompoundMixin
from ginga.canvas.CanvasMixin import CanvasMixin
from ginga.canvas import coordmap

colors_plus_none = [ None ] + colors.get_colors()

class CanvasObjectError(Exception):
    pass

class CanvasObjectBase(Callback.Callbacks):
    """This is the abstract base class for a CanvasObject.  A CanvasObject
    is an item that can be placed on a ImageViewCanvas.

    This class defines common methods used by all such objects.
    """

    def __init__(self, **kwdargs):
        if not hasattr(self, 'cb'):
            Callback.Callbacks.__init__(self)
        self.editing = False
        self.cap = 'ball'
        self.cap_radius = 4
        self.editable = True
        self.coord = 'data'
        self.ref_obj = None
        self.__dict__.update(kwdargs)
        self.data = None
        # default mapping is to data coordinates
        self.crdmap = None

        # For callbacks
        for name in ('modified', ):
            self.enable_callback(name)

    def initialize(self, tag, viewer, logger):
        self.tag = tag
        self.viewer = viewer
        self.logger = logger
        if self.crdmap is None:
            if self.coord == 'offset':
                self.crdmap = coordmap.OffsetMapper(viewer, self.ref_obj)
            else:
                self.crdmap = viewer.get_coordmap(self.coord)

    def is_editing(self):
        return self.editing

    def set_edit(self, tf):
        if not self.editable:
            raise ValueError("Object is not editable")
        self.editing = tf
        # TODO: force redraw here to show edit nodes?
        
    def set_data(self, **kwdargs):
        if self.data is None:
            self.data = Bunch.Bunch(kwdargs)
        else:
            self.data.update(kwdargs)
            
    def get_data(self, *args):
        if len(args) == 0:
            return self.data
        elif len(args) == 1:
            return self.data[args[0]]
        elif len(args) == 2:
            try:
                return self.data[args[0]]
            except KeyError:
                return args[1]
        else:
            raise CanvasObjectError("method get_data() takes at most 2 arguments")

    def redraw(self, whence=3):
        self.viewer.redraw(whence=whence)

    def use_coordmap(self, mapobj):
        self.crdmap = mapobj
        
    def canvascoords(self, x, y, center=True):
        if self.crdmap is not None:
            return self.crdmap.to_canvas(x, y)
        return self.viewer.canvascoords(x, y, center=center)

    def is_compound(self):
        return False
    
    def contains(self, x, y):
        return False
    
    def select_contains(self, x, y):
        return self.contains(x, y)
    
    def calcVertexes(self, start_x, start_y, end_x, end_y,
                     arrow_length=10, arrow_degrees=0.35):

        angle = math.atan2(end_y - start_y, end_x - start_x) + math.pi

        x1 = end_x + arrow_length * math.cos(angle - arrow_degrees);
        y1 = end_y + arrow_length * math.sin(angle - arrow_degrees);
        x2 = end_x + arrow_length * math.cos(angle + arrow_degrees);
        y2 = end_y + arrow_length * math.sin(angle + arrow_degrees);

        return (x1, y1, x2, y2)

    def calc_radius(self, x1, y1, radius):
        # scale radius
        cx1, cy1 = self.canvascoords(x1, y1)
        cx2, cy2 = self.canvascoords(x1, y1 + radius)
        # TODO: the accuracy of this calculation of radius might be improved?
        cradius = math.sqrt(abs(cy2 - cy1)**2 + abs(cx2 - cx1)**2)
        return (cx1, cy1, cradius)
    
    def swapxy(self, x1, y1, x2, y2):
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return (x1, y1, x2, y2)

    def scale_font(self):
        zoomlevel = self.viewer.get_zoom()
        if zoomlevel >= -4:
            return 14
        elif zoomlevel >= -6:
            return 12
        elif zoomlevel >= -8:
            return 10
        else:
            return 8

    def rotate_pt(self, data_x, data_y, theta, xoff=0, yoff=0):
        x, y = trcalc.rotate_pt(data_x, data_y, theta,
                                xoff=xoff, yoff=yoff)
        return x, y

    def rotate(self, theta, xoff=0, yoff=0):
        if hasattr(self, 'x'):
            self.x, self.y = self.crdmap.rotate_pt(self.x, self.y, theta,
                                                   xoff=xoff, yoff=yoff)
        elif hasattr(self, 'x1'):
            self.x1, self.y1 = self.crdmap.rotate_pt(self.x1, self.y1, theta,
                                                     xoff=xoff, yoff=yoff)
            self.x2, self.y2 = self.crdmap.rotate_pt(self.x2, self.y2, theta,
                                                     xoff=xoff, yoff=yoff)
        elif hasattr(self, 'points'):
            self.points = list(map(
                lambda p: self.crdmap.rotate_pt(p[0], p[1], theta,
                                                xoff=xoff, yoff=yoff),
                self.points))

    def rotate_by(self, theta_deg):
        ref_x, ref_y = self.get_reference_pt()
        return self.rotate(theta_deg, xoff=ref_x, yoff=ref_y)
    
    def move_delta(self, xoff, yoff):
        if hasattr(self, 'x'):
            self.x, self.y = self.crdmap.offset_pt((self.x, self.y), xoff, yoff)

        elif hasattr(self, 'x1'):
            self.x1, self.y1 = self.crdmap.offset_pt((self.x1, self.y1), xoff, yoff)
            self.x2, self.y2 = self.crdmap.offset_pt((self.x2, self.y2), xoff, yoff)
            
        elif hasattr(self, 'points'):
            for i in range(len(self.points)):
                self.points[i] = self.crdmap.offset_pt(self.points[i], xoff, yoff)

    def move_to(self, xdst, ydst):
        x, y = self.get_reference_pt()
        return self.move_delta(xdst - x, ydst - y)

    def get_num_points(self):
        if hasattr(self, 'x'):
            return 1
        elif hasattr(self, 'x1'):
            return 2
        elif hasattr(self, 'points'):
            return(len(self.points))
        else:
            return 0

    def set_point_by_index(self, i, pt):
        if hasattr(self, 'points'):
            self.points[i] = pt
        elif i == 0:
            if hasattr(self, 'x'):
                self.x, self.y = pt
            elif hasattr(self, 'x1'):
                self.x1, self.y1 = pt
        elif i == 1:
            self.x2, self.y2 = pt
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_point_by_index(self, i):
        if hasattr(self, 'points'):
            return self.points[i]
        elif i == 0:
            if hasattr(self, 'x'):
                return self.x, self.y
            elif hasattr(self, 'x1'):
                return self.x1, self.y1
        elif i == 1:
            return self.x2, self.y2
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def scale_by(self, scale_x, scale_y):
        if hasattr(self, 'radius'):
            self.radius *= max(scale_x, scale_y)

        elif hasattr(self, 'xradius'):
            self.xradius *= scale_x
            self.yradius *= scale_y

        elif hasattr(self, 'x1'):
            ctr_x, ctr_y = self.get_center_pt()
            pts = [(self.x1, self.y1), (self.x2, self.y2)]
            P = numpy.array(pts)
            P[:, 0] = (P[:, 0] - ctr_x) * scale_x + ctr_x
            P[:, 1] = (P[:, 1] - ctr_y) * scale_y + ctr_y
            self.x1, self.y1 = P[0, 0], P[0, 1]
            self.x2, self.y2 = P[1, 0], P[1, 1]
            
        elif hasattr(self, 'points'):
            ctr_x, ctr_y = self.get_center_pt()
            P = numpy.array(self.points)
            P[:, 0] = (P[:, 0] - ctr_x) * scale_x + ctr_x
            P[:, 1] = (P[:, 1] - ctr_y) * scale_y + ctr_y
            self.points = list(P)

    def convert_mapper(self, tomap):
        """
        Converts our object from using one coordinate map to another.

        NOTE: This is currently NOT WORKING, because radii are not
        converted correctly.
        """
        frommap = self.crdmap
        if frommap == tomap:
            return
        
        # convert radii
        if hasattr(self, 'radius'):
            xc, yc = self.get_center_pt()
            # get data coordinates of a point radius away from center
            # under current coordmap
            x1, y1 = frommap.to_data(xc, yc)
            x2, y2 = frommap.to_data(xc + self.radius, yc)
            x3, y3 = frommap.to_data(xc, yc + self.radius)
            # now convert these data coords to native coords in tomap
            nx1, ny1 = tomap.data_to(x1, y1)
            nx2, ny2 = tomap.data_to(x2, y2)
            nx3, ny3 = tomap.data_to(x3, y3)
            # recalculate radius using new coords
            self.radius = math.sqrt((nx2 - nx1)**2 + (ny3 - ny1)**2)

        elif hasattr(self, 'xradius'):
            # similar to above case, but there are 2 radii
            xc, yc = self.get_center_pt()
            x1, y1 = frommap.to_data(xc, yc)
            x2, y2 = frommap.to_data(xc + self.xradius, yc)
            x3, y3 = frommap.to_data(xc, yc + self.yradius)
            nx1, ny1 = tomap.data_to(x1, y1)
            nx2, ny2 = tomap.data_to(x2, y2)
            nx3, ny3 = tomap.data_to(x3, y3)
            self.xradius = math.fabs(nx2 - nx1)
            self.yradius = math.fabs(ny3 - ny1)
        
        # convert points
        for i in range(self.get_num_points()):
            # convert each point by going to data coords under old map
            # and then to native coords in the new map
            x, y = self.get_point_by_index(i)
            data_x, data_y = frommap.to_data(x, y)
            new_x, new_y = tomap.data_to(data_x, data_y)
            self.set_point_by_index(i, (new_x, new_y))

        # set our map to the new map
        self.crdmap = tomap
    
    # TODO: move these into utility module?
    #####
    def within_radius(self, a, b, x, y, canvas_radius):
        """Point (a, b) and point (x, y) are in data coordinates.
        Return True if point (a, b) is within the circle defined by
        a center at point (x, y) and within canvas_radius.
        The distance between points is scaled by the canvas scale.
        """
        scale_x, scale_y = self.viewer.get_scale_xy()
        dx = math.fabs(x - a) * scale_x
        dy = math.fabs(y - b) * scale_y
        new_radius = math.sqrt(dx**2 + dy**2)
        if new_radius <= canvas_radius:
            return True
        return False

    def get_pt(self, points, x, y, canvas_radius=None):
        if canvas_radius is None:
            canvas_radius = self.cap_radius

        if hasattr(self, 'rot_deg'):
            # rotate point back to cartesian alignment for test
            ctr_x, ctr_y = self.crdmap.to_data(*self.get_center_pt())
            xp, yp = self.rotate_pt(x, y, -self.rot_deg,
                                    xoff=ctr_x, yoff=ctr_y)
        else:
            xp, yp = x, y

        for i in range(len(points)):
            a, b = points[i]
            if self.within_radius(xp, yp, a, b, canvas_radius):
                return i
        return None

    def point_within_line(self, a, b, x1, y1, x2, y2, canvas_radius):
        # TODO: is there an algorithm with the cross and dot products
        # that is more efficient?
        r = canvas_radius
        xmin, xmax = min(x1, x2) - r, max(x1, x2) + r
        ymin, ymax = min(y1, y2) - r, max(y1, y2) + r
        if (xmin <= a <= xmax) and (ymin <= b <= ymax):
            div = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            # TODO: check for divisor almost 0-- if so then the line is
            # very short and it can be treated as a point comparison
            d = abs((x2 - x1)*(y1 - b) - (x1 - a)*(y2 - y1)) / div
            contains = (d <= canvas_radius)
            #print("res=%s" % (contains))
            return contains
        return False

    def within_line(self, a, b, x1, y1, x2, y2, canvas_radius):
        """Point (a, b) and points (x1, y1), (x2, y2) are in data coordinates.
        Return True if point (a, b) is within the line defined by
        a line from (x1, y1) to (x2, y2) and within canvas_radius.
        The distance between points is scaled by the canvas scale.
        """
        scale_x, scale_y = self.viewer.get_scale_xy()
        new_radius = canvas_radius * 1.0 / min(scale_x, scale_y)
        return self.point_within_line(a, b, x1, y1, x2, y2, new_radius)
    #####
        
    def get_points(self):
        return []
    
    def get_center_pt(self):
        # default is geometric average of points
        P = numpy.array(self.get_points())
        x = P[:, 0]
        y = P[:, 1]
        Cx = numpy.sum(x) / float(len(x))
        Cy = numpy.sum(y) / float(len(y))
        return (Cx, Cy)

    def get_reference_pt(self):
        return self.get_center_pt()

    def get_cpoints(self, points=None):
        if points is None:
            points = self.get_points()
        if hasattr(self, 'rot_deg') and self.rot_deg != 0.0:
            # rotate vertices according to rotation
            x, y = self.get_center_pt()
            rpoints = tuple(map(lambda p: self.crdmap.rotate_pt(p[0], p[1],
                                                                self.rot_deg,
                                                                xoff=x, yoff=y),
                                points))
        else:
            rpoints = points
        cpoints = tuple(map(lambda p: self.crdmap.to_canvas(p[0], p[1]),
                            rpoints))
        return cpoints


#
#   ==== BASE CLASSES FOR GRAPHICS OBJECTS ====
#
class TextBase(CanvasObjectBase):
    """Draws text on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates in the data space
    text: the text to draw
    Optional parameters for fontsize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of lower left of text"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of lower left of text"),
            Param(name='text', type=str, default='EDIT ME', 
                  description="Text to display"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of text"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x, y, text='EDIT ME',
                 font='Sans Serif', fontsize=None,
                 color='yellow', alpha=1.0, showcap=False, **kwdargs):
        self.kind = 'text'
        super(TextBase, self).__init__(color=color, alpha=alpha,
                                       x=x, y=y, font=font, fontsize=fontsize,
                                       text=text, showcap=showcap, **kwdargs)

    def get_center_pt(self):
        return (self.x, self.y)

    def select_contains(self, x, y):
        return self.within_radius(x, y, self.x, self.y, self.cap_radius)
    
    def get_points(self):
        return [self.get_center_pt()]
    
    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        # TODO: edit point for scaling or rotating?
        return [(self.x, self.y)]


class PolygonMixin(object):
    """Mixin for polygon-based objects.
    """

    def get_center_pt(self):
        P = numpy.array(self.points + [self.points[0]])
        x = P[:, 0]
        y = P[:, 1]

        a = x[:-1] * y[1:]
        b = y[:-1] * x[1:]
        A = numpy.sum(a - b) / 2.
        
        cx = x[:-1] + x[1:]
        cy = y[:-1] + y[1:]

        Cx = numpy.sum(cx * (a - b)) / (6. * A)
        Cy = numpy.sum(cy * (a - b)) / (6. * A)
        return (Cx, Cy)
    
    def get_points(self):
        return self.points

    def contains(self, xp, yp):
        # NOTE: we use a version of the ray casting algorithm
        # See: http://alienryderflex.com/polygon/
        result = False
        xj, yj = self.crdmap.to_data(*self.points[-1])
        for point in self.points:
            xi, yi = self.crdmap.to_data(*point)
            if ((((yi < yp) and (yj >= yp)) or
                 ((yj < yp) and (yi >= yp))) and
                ((xi <= xp) or (xj <= xp))):
                cross = (xi + float(yp - yi)/(yj - yi)*(xj - xi)) < xp
                result ^= cross
            xj, yj = xi, yi

        return result
            
    def set_edit_point(self, i, pt):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i-1 < len(self.points):
            self.set_point_by_index(i-1, pt)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [self.get_center_pt()] + self.points


class PolygonBase(PolygonMixin, CanvasObjectBase):
    """Draws a polygon on a ImageViewCanvas.
    Parameters are:
    List of (x, y) points in the polygon.  The last one is assumed to
    be connected to the first.
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            ## Param(name='points', type=list, default=[], argpos=0,
            ##       description="points making up polygon"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, points, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0,
                 fillalpha=1.0, **kwdargs):
        self.kind = 'polygon'
        
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, alpha=alpha,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha, **kwdargs)
        PolygonMixin.__init__(self)

class PathBase(PolygonMixin, CanvasObjectBase):
    """Draws a path on a ImageViewCanvas.
    Parameters are:
    List of (x, y) points in the polygon.  
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=['data', 'wcs'],
                  description="Set type of coordinates"),
            ## Param(name='points', type=list, default=[], argpos=0,
            ##       description="points making up polygon"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, points, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 alpha=1.0, **kwdargs):
        self.kind = 'path'
        
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, alpha=alpha,
                                  **kwdargs)
        PolygonMixin.__init__(self)
        
    def contains(self, x, y):
        x1, y1 = self.crdmap.to_data(*self.points[0])
        for point in self.points[1:]:
            x2, y2 = self.crdmap.to_data(*point)
            if self.within_line(x, y, x1, y1, x2, y2, 1.0):
                return True
            x1, y1 = x2, y2
        return False
            
    def select_contains(self, x, y):
        x1, y1 = self.crdmap.to_data(*self.points[0])
        for point in self.points[1:]:
            x2, y2 = self.crdmap.to_data(*point)
            if self.within_line(x, y, x1, y1, x2, y2, self.cap_radius):
                return True
            x1, y1 = x2, y2
        return False


class OnePointTwoRadiusMixin(object):

    def get_center_pt(self):
        return (self.x, self.y)

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            x, y = pt
            self.xradius = abs(x - self.x)
        elif i == 2:
            x, y = pt
            self.yradius = abs(y - self.y)
        elif i == 3:
            x, y = pt
            self.xradius, self.yradius = abs(x - self.x), abs(y - self.y)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [(self.x, self.y),    # location
                (self.x + self.xradius, self.y),  # adj xradius
                (self.x, self.y + self.yradius),  # adj yradius
                (self.x + self.xradius, self.y + self.yradius)]   # adj both

    def rotate_by(self, theta_deg):
        new_rot = math.fmod(self.rot_deg + theta_deg, 360.0)
        self.rot_deg = new_rot
        return new_rot


class BoxBase(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws a box on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='xradius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0,  argpos=3,
                  min=0.0,
                  description="Y radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
            ]
    
    def __init__(self, x, y, xradius, yradius, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, xradius=xradius,
                                  yradius=yradius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)
        self.kind = 'box'

    def get_points(self):
        points = ((self.x - self.xradius, self.y - self.yradius),
                  (self.x + self.xradius, self.y - self.yradius),
                  (self.x + self.xradius, self.y + self.yradius),
                  (self.x - self.xradius, self.y + self.yradius))
        return points
    
    def contains(self, data_x, data_y):
        x1, y1 = self.crdmap.to_data(self.x - self.xradius,
                                     self.y - self.yradius)
        x2, y2 = self.crdmap.to_data(self.x + self.xradius,
                                     self.y + self.yradius)

        # rotate point back to cartesian alignment for test
        xd, yd = self.crdmap.to_data(self.x, self.y)
        xp, yp = self.rotate_pt(data_x, data_y, -self.rot_deg,
                                xoff=xd, yoff=yd)
        if (min(x1, x2) <= xp <= max(x1, x2) and
            min(y1, y2) <= yp <= max(y1, y2)):
            return True
        return False


class EllipseBase(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws an ellipse on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='xradius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0,  argpos=3,
                  min=0.0,
                  description="Y radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
            ]
    
    def __init__(self, x, y, xradius, yradius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, xradius=xradius,
                                  yradius=yradius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)
        self.kind = 'ellipse'

    def get_points(self):
        return [self.get_center_pt()]
    
    def contains(self, data_x, data_y):
        # rotate point back to cartesian alignment for test
        xd, yd = self.crdmap.to_data(self.x, self.y)
        xp, yp = self.rotate_pt(data_x, data_y, -self.rot_deg,
                                xoff=xd, yoff=yd)

        # need to recalculate radius in case of wcs coords
        x2, y2 = self.crdmap.to_data(self.x + self.xradius,
                                     self.y + self.yradius)
        xradius = max(x2, xd) - min(x2, xd)
        yradius = max(y2, yd) - min(y2, yd)
        
        # See http://math.stackexchange.com/questions/76457/check-if-a-point-is-within-an-ellipse
        res = (((xp - xd) ** 2) / xradius ** 2 + 
               ((yp - yd) ** 2) / yradius ** 2)
        if res <= 1.0:
            return True
        return False

    def get_bezier_pts(self, kappa=0.5522848):
        """Used by drawing subclasses to draw the ellipse."""

        mx, my = self.x, self.y
        xs, ys = mx - self.xradius, my - self.yradius
        ox, oy = self.xradius * kappa, self.yradius * kappa
        xe, ye = mx + self.xradius, my + self.yradius
        
        pts = [(xs, my),
               (xs, my - oy), (mx - ox, ys), (mx, ys),
               (mx + ox, ys), (xe, my - oy), (xe, my),
               (xe, my + oy), (mx + ox, ye), (mx, ye),
               (mx - ox, ye), (xs, my + oy), (xs, my)]
        return pts


class TriangleBase(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws a triangle on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='xradius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0,  argpos=3,
                  min=0.0,
                  description="Y radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
            ]
    
    def __init__(self, x, y, xradius, yradius, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        self.kind='triangle'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha,
                                  x=x, y=y, xradius=xradius,
                                  yradius=yradius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)

    def get_points(self):
        return [(self.x - 2*self.xradius, self.y - self.yradius),
                (self.x + 2*self.xradius, self.y - self.yradius),
                (self.x, self.y + self.yradius)]
    
    def contains(self, data_x, data_y):
        # is this the same as self.x, self.y ?
        ctr_x, ctr_y = self.get_center_pt()
        xd, yd = self.crdmap.to_data(ctr_x, ctr_y)
        # rotate point back to cartesian alignment for test
        x, y = self.rotate_pt(data_x, data_y, -self.rot_deg,
                              xoff=xd, yoff=yd)

        (x1, y1), (x2, y2), (x3, y3) = self.get_points()
        x1, y1 = self.crdmap.to_data(x1, y1)
        x2, y2 = self.crdmap.to_data(x2, y2)
        x3, y3 = self.crdmap.to_data(x3, y3)

        # barycentric coordinate test
        denominator = ((y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3))
        a = ((y2 - y3)*(x - x3) + (x3 - x2)*(y - y3)) / denominator
        b = ((y3 - y1)*(x - x3) + (x1 - x3)*(y - y3)) / denominator
        c = 1.0 - a - b
        
        tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        return tf


class OnePointOneRadiusMixin(object):

    def get_center_pt(self):
        return (self.x, self.y)

    def get_points(self):
        return [(self.x, self.y)]
    
    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            x, y = pt
            self.radius = math.sqrt(abs(x - self.x)**2 + 
                                    abs(y - self.y)**2 )
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [(self.x, self.y),
                (self.x + self.radius, self.y)]

    def rotate_by(self, theta_deg):
        pass

class CircleBase(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a circle on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x, y, radius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, radius=radius, **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        self.kind = 'circle'

    def contains(self, data_x, data_y):
        # rotate point back to cartesian alignment for test
        xd, yd = self.crdmap.to_data(self.x, self.y)
        xp, yp = data_x, data_y

        # need to recalculate radius in case of wcs coords
        x2, y2 = self.crdmap.to_data(self.x + self.radius,
                                     self.y + self.radius)
        xradius = max(x2, xd) - min(x2, xd)
        yradius = max(y2, yd) - min(y2, yd)
        
        # See http://math.stackexchange.com/questions/76457/check-if-a-point-is-within-an-ellipse
        res = (((xp - xd) ** 2) / xradius ** 2 + 
               ((yp - yd) ** 2) / yradius ** 2)
        if res <= 1.0:
            return True
        return False

class PointBase(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a point on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, style, etc.
    Currently the only styles are 'cross' and 'plus'.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='style', type=str, default='cross',
                  valid=['cross', 'plus'],
                  description="Style of point (default 'cross')"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x, y, radius, style='cross', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0, showcap=False,
                 **kwdargs):
        self.kind = 'point'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth,
                                  linestyle=linestyle,
                                  x=x, y=y, radius=radius,
                                  showcap=showcap, style=style,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        
    def contains(self, data_x, data_y):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        if (data_x == xd) and (data_y == yd):
            return True
        return False

    def select_contains(self, data_x, data_y):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        return self.within_radius(data_x, data_y, xd, yd, self.cap_radius)
        
    def get_edit_points(self):
        return [(self.x, self.y),
                # TODO: account for point style
                (self.x + self.radius, self.y + self.radius)]


class TwoPointMixin(object):

    def get_center_pt(self):
        return ((self.x1 + self.x2) / 2., (self.y1 + self.y2) / 2.)

    def set_edit_point(self, i, pt):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        else:
            self.set_point_by_index(i-1, pt)

    def get_edit_points(self):
        return [self.get_center_pt(),
                (self.x1, self.y1), (self.x2, self.y2)]
        

class RectangleBase(TwoPointMixin, CanvasObjectBase):
    """Draws a rectangle on a ImageViewCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one corner in the data space
    x2, y2: 0-based coordinates of the opposing corner in the data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x1', type=float, default=0.0, argpos=0,
                  description="First X coordinate of object"),
            Param(name='y1', type=float, default=0.0, argpos=1,
                  description="First Y coordinate of object"),
            Param(name='x2', type=float, default=0.0, argpos=2,
                  description="Second X coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=3,
                  description="Second Y coordinate of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='drawdims', type=_bool,
                  default=False, valid=[False, True],
                  description="Annotate with dimensions of object"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0,
                 drawdims=False, font='Sans Serif', fillalpha=1.0,
                 **kwdargs):
        self.kind = 'rectangle'
        
        CanvasObjectBase.__init__(self, color=color,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  drawdims=drawdims, font=font,
                                  **kwdargs)
        TwoPointMixin.__init__(self)
        
    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y1),
                  (self.x2, self.y2), (self.x1, self.y2)]
        return points
    
    def get_llur(self):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        return self.swapxy(x1, y1, x2, y2)
        
    def contains(self, data_x, data_y):
        x1, y1, x2, y2 = self.get_llur()

        if (x1 <= data_x <= x2) and (y1 <= data_y <= y2):
            return True
        return False

    # TO BE DEPRECATED?
    def move_point(self):
        return self.get_center_pt()


class LineBase(TwoPointMixin, CanvasObjectBase):
    """Draws a line on a ImageViewCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end in the data space
    x2, y2: 0-based coordinates of the opposing end in the data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x1', type=float, default=0.0, argpos=0,
                  description="First X coordinate of object"),
            Param(name='y1', type=float, default=0.0, argpos=1,
                  description="First Y coordinate of object"),
            Param(name='x2', type=float, default=0.0, argpos=2,
                  description="Second X coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=3,
                  description="Second Y coordinate of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='arrow', type=str, default='none',
                  valid=['start', 'end', 'both', 'none'],
                  description="Arrows at ends (default: none)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 arrow=None, showcap=False, **kwdargs):
        self.kind = 'line'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, arrow=arrow,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  **kwdargs)
        TwoPointMixin.__init__(self)
        
    def get_points(self):
        return [(self.x1, self.y1), (self.x2, self.y2)]

    def select_contains(self, data_x, data_y):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        return self.within_line(data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius)
        

class RightTriangleBase(TwoPointMixin, CanvasObjectBase):
    """Draws a right triangle on a ImageViewCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end of the diagonal in the data space
    x2, y2: 0-based coordinates of the opposite end of the diagonal
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x1', type=float, default=0.0, argpos=0,
                  description="First X coordinate of object"),
            Param(name='y1', type=float, default=0.0, argpos=1,
                  description="First Y coordinate of object"),
            Param(name='x2', type=float, default=0.0, argpos=2,
                  description="Second X coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=3,
                  description="Second Y coordinate of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x1, y1, x2, y2, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        self.kind='righttriangle'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        return [(self.x1, self.y1), (self.x2, self.y2)]
    
    def contains(self, data_x, data_y):
        x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2
        x3, y3 = self.x2, self.y1

        x, y = data_x, data_y
        x1, y1 = self.crdmap.to_data(x1, y1)
        x2, y2 = self.crdmap.to_data(x2, y2)
        x3, y3 = self.crdmap.to_data(x3, y3)
        
        # barycentric coordinate test
        denominator = ((y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3))
        a = ((y2 - y3)*(x - x3) + (x3 - x2)*(y - y3)) / denominator
        b = ((y3 - y1)*(x - x3) + (x1 - x3)*(y - y3)) / denominator
        c = 1.0 - a - b
        
        tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        return tf


class CompassBase(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a WCS compass on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius of the compass arms, in data units
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='skyblue',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x, y, radius, color='skyblue',
                 linewidth=1, fontsize=None, font='Sans Serif',
                 alpha=1.0, linestyle='solid', showcap=True, **kwdargs):
        self.kind = 'compass'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  x=x, y=y, radius=radius,
                                  font=font, fontsize=fontsize,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

    def get_points(self):
        image = self.viewer.get_image()
        x, y, xn, yn, xe, ye = image.calc_compass_radius(self.x,
                                                         self.y,
                                                         self.radius)
        return [(x, y), (xn, yn), (xe, ye)]
    
    def get_edit_points(self):
        return self.get_points()

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i in (1, 2):
            x, y = pt
            self.radius = max(abs(x - self.x), abs(y - self.y))
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def select_contains(self, data_x, data_y):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        return self.within_radius(data_x, data_y, xd, yd, self.cap_radius)
        
        
class RulerBase(TwoPointMixin, CanvasObjectBase):
    """Draws a WCS ruler (like a right triangle) on a ImageViewCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end of the diagonal in the data space
    x2, y2: 0-based coordinates of the opposite end of the diagonal
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x1', type=float, default=0.0, argpos=0,
                  description="First X coordinate of object"),
            Param(name='y1', type=float, default=0.0, argpos=1,
                  description="First Y coordinate of object"),
            Param(name='x2', type=float, default=0.0, argpos=2,
                  description="Second X coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=3,
                  description="Second Y coordinate of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='lightgreen',
                  description="Color of outline"),
            Param(name='showplumb', type=_bool,
                  default=True, valid=[False, True],
                  description="Show plumb lines for the ruler"),
            Param(name='color2',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Second color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='units', type=str, default='arcmin',
                  valid=['arcmin', 'pixels'],
                  description="Units for text distance (default: arcmin)"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]
    
    def __init__(self, x1, y1, x2, y2, color='green', color2='yellow',
                 alpha=1.0, linewidth=1, linestyle='solid',
                 showcap=True, showplumb=True, units='arcmin',
                 font='Sans Serif', fontsize=None, **kwdargs):
        self.kind = 'ruler'
        CanvasObjectBase.__init__(self, color=color, color2=color2,
                                  alpha=alpha, units=units,
                                  showplumb=showplumb,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  font=font, fontsize=fontsize,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_ruler_distances(self):
        mode = self.units.lower()
        try:
            image = self.viewer.get_image()
            if mode == 'arcmin':
                # Calculate RA and DEC for the three points
                # origination point
                ra_org, dec_org = image.pixtoradec(self.x1, self.y1)

                # destination point
                ra_dst, dec_dst = image.pixtoradec(self.x2, self.y2)

                # "heel" point making a right triangle
                ra_heel, dec_heel = image.pixtoradec(self.x2, self.y1)

                text_h = wcs.get_starsep_RaDecDeg(ra_org, dec_org,
                                                  ra_dst, dec_dst)
                text_x = wcs.get_starsep_RaDecDeg(ra_org, dec_org,
                                                  ra_heel, dec_heel)
                text_y = wcs.get_starsep_RaDecDeg(ra_heel, dec_heel,
                                                  ra_dst, dec_dst)
            else:
                dx = abs(self.x2 - self.x1)
                dy = abs(self.y2 - self.y1)
                dh = math.sqrt(dx**2 + dy**2)
                text_x = str(dx)
                text_y = str(dy)
                text_h = ("%.3f" % dh)
                
        except Exception as e:
            text_h = 'BAD WCS'
            text_x = 'BAD WCS'
            text_y = 'BAD WCS'

        return (text_x, text_y, text_h)

    def get_points(self):
        return [(self.x1, self.y1), (self.x2, self.y2)]

    def select_contains(self, data_x, data_y):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        return self.within_line(data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius)


class ImageBase(CanvasObjectBase):
    """Draws an image on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of one corner in the data space
    image: the image, which must be an RGBImage object
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of corner of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of corner of object"),
            ## Param(name='image', type=?, argpos=2,
            ##       description="Image to be displayed on canvas"),
            Param(name='scale_x', type=float, default=1.0,
                  description="Scaling factor for X dimension of object"),
            Param(name='scale_y', type=float, default=1.0,
                  description="Scaling factor for Y dimension of object"),
            Param(name='linewidth', type=int, default=0,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='lightgreen',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ## Param(name='flipy', type=_bool,
            ##       default=True, valid=[False, True],
            ##       description="Flip image in Y direction"),
            Param(name='optimize', type=_bool,
                  default=True, valid=[False, True],
                  description="Optimize rendering for this object"),
            ]
    
    def __init__(self, x, y, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 linewidth=0, linestyle='solid', color='lightgreen',
                 showcap=False, flipy=False, optimize=True,
                 **kwdargs):
        self.kind = 'image'
        super(ImageBase, self).__init__(x=x, y=y, image=image, alpha=alpha,
                                        scale_x=scale_x, scale_y=scale_y,
                                        linewidth=linewidth, linestyle=linestyle,
                                        color=color, showcap=showcap,
                                        flipy=flipy, optimize=optimize,
                                        **kwdargs)

        self._drawn = False
        # these hold intermediate step results. Depending on value of
        # `whence` they may not need to be recomputed.
        self._cutout = None
        # calculated location of overlay on canvas
        self._cvs_x = 0
        self._cvs_y = 0
        self._zorder = 0
        # images are not editable by default
        self.editable = False

    def get_zorder(self):
        return self._zorder

    def set_zorder(self, zorder, redraw=True):
        self._zorder = zorder
        self.viewer.reorder_layers()
        if redraw:
            self.viewer.redraw(whence=2)

    def draw(self):
        if not self._drawn:
            self._drawn = True
            self.viewer.redraw(whence=2)
    
    def draw_image(self, dstarr, whence=0.0):
        #print("redraw whence=%f" % (whence))
        dst_order = self.viewer.get_rgb_order()
        image_order = self.image.get_order()

        if (whence <= 0.0) or (self._cutout is None) or (not self.optimize):
            # get extent of our data coverage in the window
            ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) = self.viewer.get_pan_rect()
            xmin = int(min(x0, x1, x2, x3))
            ymin = int(min(y0, y1, y2, y3))
            xmax = int(max(x0, x1, x2, x3))
            ymax = int(max(y0, y1, y2, y3))

            # destination location in data_coords
            #dst_x, dst_y = self.x, self.y + ht
            dst_x, dst_y = self.x, self.y

            a1, b1, a2, b2 = 0, 0, self.image.width, self.image.height

            # calculate the cutout that we can make and scale to merge
            # onto the final image--by only cutting out what is necessary
            # this speeds scaling greatly at zoomed in sizes
            dst_x, dst_y, a1, b1, a2, b2 = \
                   trcalc.calc_image_merge_clip(xmin, ymin, xmax, ymax,
                                                dst_x, dst_y, a1, b1, a2, b2)

            # is image completely off the screen?
            if (a2 - a1 <= 0) or (b2 - b1 <= 0):
                # no overlay needed
                #print "no overlay needed"
                return

            # cutout and scale the piece appropriately by the viewer scale
            scale_x, scale_y = self.viewer.get_scale_xy()
            # scale additionally by our scale
            _scale_x, _scale_y = scale_x * self.scale_x, scale_y * self.scale_y
            
            res = self.image.get_scaled_cutout(a1, b1, a2, b2,
                                               _scale_x, _scale_y,
                                               #flipy=self.flipy,
                                               method='basic')

            # don't ask for an alpha channel from overlaid image if it
            # doesn't have one
            dst_order = self.viewer.get_rgb_order()
            image_order = self.image.get_order()
            ## if ('A' in dst_order) and not ('A' in image_order):
            ##     dst_order = dst_order.replace('A', '')

            ## if dst_order != image_order:
            ##     # reorder result to match desired rgb_order by backend
            ##     self._cutout = trcalc.reorder_image(dst_order, res.data,
            ##                                         image_order)
            ## else:
            ##     self._cutout = res.data
            self._cutout = res.data

            # calculate our offset from the pan position
            pan_x, pan_y = self.viewer.get_pan()
            pan_off = self.viewer.data_off
            pan_x, pan_y = pan_x + pan_off, pan_y + pan_off
            #print "pan x,y=%f,%f" % (pan_x, pan_y)
            off_x, off_y = dst_x - pan_x, dst_y - pan_y
            # scale offset
            off_x *= scale_x
            off_y *= scale_y
            #print "off_x,y=%f,%f" % (off_x, off_y)

            # dst position in the pre-transformed array should be calculated
            # from the center of the array plus offsets
            ht, wd, dp = dstarr.shape
            self._cvs_x = int(round(wd / 2.0  + off_x))
            self._cvs_y = int(round(ht / 2.0  + off_y))

        # composite the image into the destination array at the
        # calculated position
        trcalc.overlay_image(dstarr, self._cvs_x, self._cvs_y, self._cutout,
                             dst_order=dst_order, src_order=image_order,
                             alpha=self.alpha, flipy=False)

    def _reset_optimize(self):
        self._drawn = False
        self._cutout = None
        
    def set_image(self, image):
        self.image = image
        self._reset_optimize()

    def get_scaled_wdht(self):
        width = int(self.image.width * self.scale_x)
        height = int(self.image.height * self.scale_y)
        return (width, height)
    
    def get_coords(self):
        x1, y1 = self.x, self.y
        wd, ht = self.get_scaled_wdht()
        x2, y2 = x1 + wd, y1 + ht
        return (x1, y1, x2, y2)

    def get_center_pt(self):
        wd, ht = self.get_scaled_wdht()
        return (self.x + wd / 2.0, self.y + ht / 2.0)

    def get_points(self):
        x1, y1, x2, y2 = self.get_coords()
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    
    def contains(self, data_x, data_y):
        width, height = self.get_scaled_wdht()
        x2, y2 = self.x + width, self.y + height
        if ((self.x <= x < x2) and (self.y <= y < y2)):
            return True
        return False

    def rotate(self, theta, xoff=0, yoff=0):
        raise ValueError("Images cannot be rotated")

    def set_edit_point(self, i, pt):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i == 1:
            x, y = pt
            self.scale_x = abs(x - self.x) / float(self.image.width)
        elif i == 2:
            x, y = pt
            self.scale_y = abs(y - self.y) / float(self.image.height)
        elif i == 3:
            x, y = pt
            self.scale_x = abs(x - self.x) / float(self.image.width)
            self.scale_y = abs(y - self.y) / float(self.image.height)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

        self._reset_optimize()

    def get_edit_points(self):
        width, height = self.get_scaled_wdht()
        return [self.get_center_pt(),    # location
                (self.x + width, self.y + height / 2.),
                (self.x + width / 2., self.y + height),
                (self.x + width, self.y + height)
                ]

    def scale_by(self, scale_x, scale_y):
        self.scale_x *= scale_x
        self.scale_y *= scale_y
        self._reset_optimize()

    def set_scale(self, scale_x, scale_y):
        self.scale_x = scale_x
        self.scale_y = scale_y
        self._reset_optimize()

    def set_origin(self, x, y):
        self.x, self.y = x, y
        self._reset_optomize()


class NormImageBase(ImageBase):
    """Draws an image on a ImageViewCanvas.

    Parameters are:
    x, y: 0-based coordinates of one corner in the data space
    image: the image, which must be an RGBImage object
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of corner of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of corner of object"),
            ## Param(name='image', type=?, argpos=2,
            ##       description="Image to be displayed on canvas"),
            Param(name='scale_x', type=float, default=1.0,
                  description="Scaling factor for X dimension of object"),
            Param(name='scale_y', type=float, default=1.0,
                  description="Scaling factor for Y dimension of object"),
            Param(name='linewidth', type=int, default=0,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color', 
                  valid=colors_plus_none, type=_color, default='lightgreen',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ## Param(name='flipy', type=_bool,
            ##       default=True, valid=[False, True],
            ##       description="Flip image in Y direction"),
            Param(name='optimize', type=_bool,
                  default=True, valid=[False, True],
                  description="Optimize rendering for this object"),
            ## Param(name='rgbmap', type=?,
            ##       description="RGB mapper for the image"),
            ## Param(name='autocuts', type=?,
            ##       description="Cuts manager for the image"),
            ]
    
    def __init__(self, x, y, image, alpha=1.0, scale_x=1.0, scale_y=1.0, 
                 linewidth=0, linestyle='solid', color='lightgreen', showcap=False,
                 optimize=True, rgbmap=None, autocuts=None, **kwdargs):
        self.kind = 'normimage'
        super(NormImageBase, self).__init__(x=x, y=y, image=image, alpha=alpha,
                                            scale_x=scale_x, scale_y=scale_y,
                                            linewidth=linewidth, linestyle=linestyle,
                                            color=color,
                                            showcap=showcap, optimize=optimize,
                                            **kwdargs)
        self.rgbmap = rgbmap
        self.autocuts = autocuts

        # these hold intermediate step results. Depending on value of
        # `whence` they may not need to be recomputed.
        self._prergb = None
        self._rgbarr = None

    def draw_image(self, dstarr, whence=0.0):
        #print("redraw whence=%f" % (whence))

        if (whence <= 0.0) or (self._cutout is None) or (not self.optimize):
            # get extent of our data coverage in the window
            ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) = self.viewer.get_pan_rect()
            xmin = int(min(x0, x1, x2, x3))
            ymin = int(min(y0, y1, y2, y3))
            xmax = int(max(x0, x1, x2, x3))
            ymax = int(max(y0, y1, y2, y3))

            # destination location in data_coords
            dst_x, dst_y = self.x, self.y

            a1, b1, a2, b2 = 0, 0, self.image.width, self.image.height

            # calculate the cutout that we can make and scale to merge
            # onto the final image--by only cutting out what is necessary
            # this speeds scaling greatly at zoomed in sizes
            dst_x, dst_y, a1, b1, a2, b2 = \
                   trcalc.calc_image_merge_clip(xmin, ymin, xmax, ymax,
                                                dst_x, dst_y, a1, b1, a2, b2)

            # is image completely off the screen?
            if (a2 - a1 <= 0) or (b2 - b1 <= 0):
                # no overlay needed
                #print "no overlay needed"
                return

            # cutout and scale the piece appropriately by viewer scale
            scale_x, scale_y = self.viewer.get_scale_xy()
            # scale additionally by our scale
            _scale_x, _scale_y = scale_x * self.scale_x, scale_y * self.scale_y
            
            res = self.image.get_scaled_cutout(a1, b1, a2, b2,
                                               _scale_x, _scale_y)
            self._cutout = res.data

            # calculate our offset from the pan position
            pan_x, pan_y = self.viewer.get_pan()
            pan_off = self.viewer.data_off
            pan_x, pan_y = pan_x + pan_off, pan_y + pan_off
            #print "pan x,y=%f,%f" % (pan_x, pan_y)
            off_x, off_y = dst_x - pan_x, dst_y - pan_y
            # scale offset
            off_x *= scale_x
            off_y *= scale_y
            #print "off_x,y=%f,%f" % (off_x, off_y)

            # dst position in the pre-transformed array should be calculated
            # from the center of the array plus offsets
            ht, wd, dp = dstarr.shape
            self._cvs_x = int(round(wd / 2.0  + off_x))
            self._cvs_y = int(round(ht / 2.0  + off_y))

        if self.rgbmap is not None:
            rgbmap = self.rgbmap
        else:
            rgbmap = self.viewer.get_rgbmap()

        if (whence <= 1.0) or (self._prergb is None) or (not self.optimize):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = rgbmap.get_hash_size() - 1
            newdata = self.apply_visuals(self._cutout, 0, vmax)

            # result becomes an index array fed to the RGB mapper
            if not numpy.issubdtype(newdata.dtype, numpy.dtype('uint')):
                newdata = newdata.astype(numpy.uint)
            idx = newdata

            self.logger.debug("shape of index is %s" % (str(idx.shape)))
            self._prergb = idx

        dst_order = self.viewer.get_rgb_order()
        image_order = self.image.get_order()
        get_order = dst_order
        if ('A' in dst_order) and not ('A' in image_order):
            get_order = dst_order.replace('A', '')

        if (whence <= 2.5) or (self._rgbarr is None) or (not self.optimize):
            # get RGB mapped array
            rgbobj = rgbmap.get_rgbarray(self._prergb, order=dst_order,
                                         image_order=image_order)
            self._rgbarr = rgbobj.get_array(get_order)

        # composite the image into the destination array at the
        # calculated position
        trcalc.overlay_image(dstarr, self._cvs_x, self._cvs_y, self._rgbarr,
                             dst_order=dst_order, src_order=get_order,
                             alpha=self.alpha, flipy=False)

    def apply_visuals(self, data, vmin, vmax):
        if self.autocuts is not None:
            autocuts = self.autocuts
        else:
            autocuts = self.viewer.autocuts

        # Apply cut levels
        loval, hival = self.viewer.t_['cuts']
        newdata = autocuts.cut_levels(data, loval, hival,
                                      vmin=vmin, vmax=vmax)
        return newdata

    def _reset_optimize(self):
        super(NormImageBase, self)._reset_optimize()
        self._prergb = None
        self._rgbarr = None
        
    def set_image(self, image):
        self.image = image
        self._reset_optimize()

    def scale_by(self, scale_x, scale_y):
        #print("scaling image")
        self.scale_x *= scale_x
        self.scale_y *= scale_y
        self._reset_optimize()
        #print("image scale_x=%f scale_y=%f" % (self.scale_x, self.scale_y))


class CompoundObject(CompoundMixin, CanvasObjectBase):
    """Compound object on a ImageViewCanvas.
    Parameters are:
    the child objects making up the compound object.  Objects are drawn
    in the order listed.
    Example:
      CompoundObject(Point(x, y, radius, ...),
      Circle(x, y, radius, ...))
    This makes a point inside a circle.
    """

    def __init__(self, *objects):
        CanvasObjectBase.__init__(self)
        CompoundMixin.__init__(self)
        self.kind = 'compound'
        self.objects = list(objects)
        self.editable = False


class Canvas(CanvasMixin, CompoundObject, CanvasObjectBase):
    def __init__(self, *objects):
        CanvasObjectBase.__init__(self)
        CompoundObject.__init__(self, *objects)
        CanvasMixin.__init__(self)
        self.kind = 'canvas'
        self.editable = False


# funky boolean converter
_bool = lambda st: str(st).lower() == 'true'

# color converter
_color = lambda name: name

# END
