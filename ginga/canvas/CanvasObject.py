#
# CanvasObject.py -- classes for shapes drawn on ginga canvases.
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
from ginga import trcalc, colors
from ginga.util.six.moves import map

from . import coordmap

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
        self.cap = 'ball'
        self.cap_radius = 4
        self.editable = True
        self.coord = 'data'
        self.ref_obj = None
        self.__dict__.update(kwdargs)
        self.data = None
        # default mapping is to data coordinates
        self.crdmap = None
        # For debugging
        self.name = None

        ## # For callbacks
        ## for name in ('modified', ):
        ##     self.enable_callback(name)

    def initialize(self, tag, viewer, logger):
        self.tag = tag
        self.viewer = viewer
        self.logger = logger
        if self.crdmap is None:
            if self.coord == 'offset':
                self.crdmap = coordmap.OffsetMapper(viewer, self.ref_obj)
            else:
                self.crdmap = viewer.get_coordmap(self.coord)

    def sync_state(self):
        """This method called when changes are made to the parameters.
        subclasses should override if they need any special state handling.
        """
        pass

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

    def use_coordmap(self, mapobj):
        self.crdmap = mapobj

    def canvascoords(self, viewer, x, y, center=True):
        # if object has a valid coordinate map, use it
        crdmap = self.crdmap
        if crdmap is None:
            # otherwise get viewer's default one
            crdmap = viewer.get_coordmap('data')

        # convert coordinates to data coordinates
        data_x, data_y = crdmap.to_data(x, y)

        # finally, convert to viewer's canvas coordinates
        return viewer.get_canvas_xy(data_x, data_y, center=center)

    ## def canvascoords(self, viewer, x, y, center=True):
    ##     crdmap = viewer.get_coordmap(self.coord)

    ##     # convert coordinates to data coordinates
    ##     data_x, data_y = crdmap.to_data(x, y)

    ##     # finally, convert to viewer's canvas coordinates
    ##     return viewer.get_canvas_xy(data_x, data_y, center=center)

    def is_compound(self):
        return False

    def contains_arr(self, x_arr, y_arr):
        contains = numpy.array([False] * len(x_arr))
        return contains

    def contains(self, x, y):
        return False

    def select_contains(self, viewer, x, y):
        return self.contains(x, y)

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calc_vertexes(x1, y1, x2, y2)

        alpha = getattr(self, 'alpha', 1.0)
        cr.set_fill(self.color, alpha=alpha)
        cr.draw_polygon(((x2, y2), (i1, j1), (i2, j2)))
        cr.set_fill(None)

    def draw_caps(self, cr, cap, points, radius=None, isedit=False):
        i = 0
        for cx, cy in points:
            if radius is None:
                radius = self.cap_radius
            alpha = getattr(self, 'alpha', 1.0)
            if cap == 'ball':
                # Draw move control point in a different color than the others
                # (move cp is always cp #0)
                if (i == 0) and isedit:
                    # TODO: configurable
                    color = 'orangered'
                else:
                    color = self.color

                cr.set_fill(color, alpha=alpha)
                cr.draw_circle(cx, cy, radius)
                #cr.set_fill(self, None)
            i += 1

    def draw_edit(self, cr, viewer):
        cpoints = self.get_cpoints(viewer, points=self.get_edit_points())
        self.draw_caps(cr, 'ball', cpoints, isedit=True)

    def calc_radius(self, viewer, x1, y1, radius):
        # scale radius
        cx1, cy1 = self.canvascoords(viewer, x1, y1)
        cx2, cy2 = self.canvascoords(viewer, x1, y1 + radius)
        # TODO: the accuracy of this calculation of radius might be improved?
        cradius = math.sqrt(abs(cy2 - cy1)**2 + abs(cx2 - cx1)**2)
        return (cx1, cy1, cradius)

    def calc_vertexes(self, start_cx, start_cy, end_cx, end_cy,
                     arrow_length=10, arrow_degrees=0.35):

        angle = math.atan2(end_cy - start_cy, end_cx - start_cx) + math.pi

        cx1 = end_cx + arrow_length * math.cos(angle - arrow_degrees);
        cy1 = end_cy + arrow_length * math.sin(angle - arrow_degrees);
        cx2 = end_cx + arrow_length * math.cos(angle + arrow_degrees);
        cy2 = end_cy + arrow_length * math.sin(angle + arrow_degrees);

        return (cx1, cy1, cx2, cy2)

    def swapxy(self, x1, y1, x2, y2):
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return (x1, y1, x2, y2)

    def scale_font(self, viewer):
        zoomlevel = viewer.get_zoom()
        if zoomlevel >= -4:
            return 14
        elif zoomlevel >= -6:
            return 12
        elif zoomlevel >= -8:
            return 10
        else:
            return 8

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
        self.rotate(theta_deg, xoff=ref_x, yoff=ref_y)

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
    def point_within_radius(self, a_arr, b_arr, x, y, canvas_radius,
                            scale_x=1.0, scale_y=1.0):
        """Point (a, b) and point (x, y) are in data coordinates.
        Return True if point (a, b) is within the circle defined by
        a center at point (x, y) and within canvas_radius.
        """
        dx = numpy.fabs(x - a_arr) * scale_x
        dy = numpy.fabs(y - b_arr) * scale_y
        new_radius = numpy.sqrt(dx**2 + dy**2)
        res = (new_radius <= canvas_radius)
        return res

    def within_radius(self, viewer, a_arr, b_arr, x, y, canvas_radius):
        """Point (a, b) and point (x, y) are in data coordinates.
        Return True if point (a, b) is within the circle defined by
        a center at point (x, y) and within canvas_radius.
        The distance between points is scaled by the canvas scale.
        """
        scale_x, scale_y = viewer.get_scale_xy()
        return self.point_within_radius(a_arr, b_arr, x, y, canvas_radius,
                                        scale_x=scale_x, scale_y=scale_y)

    def get_pt(self, viewer, points, x, y, canvas_radius=None):
        if canvas_radius is None:
            canvas_radius = self.cap_radius

        if hasattr(self, 'rot_deg'):
            # rotate point back to cartesian alignment for test
            ctr_x, ctr_y = self.crdmap.to_data(*self.get_center_pt())
            xp, yp = trcalc.rotate_pt(x, y, -self.rot_deg,
                                      xoff=ctr_x, yoff=ctr_y)
        else:
            xp, yp = x, y

        # TODO: do this using numpy array()
        for i in range(len(points)):
            a, b = points[i]
            if self.within_radius(viewer, xp, yp, a, b, canvas_radius):
                return i
        return None

    def point_within_line(self, a_arr, b_arr, x1, y1, x2, y2,
                          canvas_radius):
        # TODO: is there an algorithm with the cross and dot products
        # that is more efficient?
        r = canvas_radius
        xmin, xmax = min(x1, x2) - r, max(x1, x2) + r
        ymin, ymax = min(y1, y2) - r, max(y1, y2) + r
        div = numpy.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        d = numpy.fabs((x2 - x1)*(y1 - b_arr) - (x1 - a_arr)*(y2 - y1)) / div

        ## contains = (xmin <= a_arr <= xmax) and (ymin <= b_arr <= ymax) and \
        ##            (d <= canvas_radius)
        contains = numpy.logical_and(
            numpy.logical_and(xmin <= a_arr, a_arr <= xmax),
            numpy.logical_and(d <= canvas_radius,
                              numpy.logical_and(ymin <= b_arr, b_arr <= ymax)))
        return contains

    def within_line(self, viewer, a_arr, b_arr, x1, y1, x2, y2,
                    canvas_radius):
        """Point (a, b) and points (x1, y1), (x2, y2) are in data coordinates.
        Return True if point (a, b) is within the line defined by
        a line from (x1, y1) to (x2, y2) and within canvas_radius.
        The distance between points is scaled by the canvas scale.
        """
        scale_x, scale_y = viewer.get_scale_xy()
        new_radius = canvas_radius * 1.0 / min(scale_x, scale_y)
        return self.point_within_line(a_arr, b_arr, x1, y1, x2, y2,
                                         new_radius)

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

    def get_cpoints(self, viewer, points=None):
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
        cpoints = tuple(map(lambda p: self.canvascoords(viewer, p[0], p[1]),
                            rpoints))
        return cpoints

    def get_bbox(self):
        """
        Get lower-left and upper-right coordinates of the bounding box
        of this compound object.

        Returns
        -------
        x1, y1, x2, y2: a 4-tuple of the lower-left and upper-right coords
        """
        x1, y1, x2, y2 = self.get_llur()
        return ((x1, y1), (x1, y2), (x2, y2), (x2, y1))


# this is the data structure to which drawing classes are registered
drawCatalog = Bunch.Bunch(caseless=True)

def get_canvas_types():
    # force registration of all canvas types
    import ginga.canvas.types.all

    return drawCatalog

def get_canvas_type(name):
    # force registration of all canvas types
    import ginga.canvas.types.all

    return drawCatalog[name]

def register_canvas_type(name, klass):
    global drawCatalog
    drawCatalog[name] = klass

def register_canvas_types(klass_dict):
    global drawCatalog
    drawCatalog.update(klass_dict)

# funky boolean converter
_bool = lambda st: str(st).lower() == 'true'

# color converter
_color = lambda name: name


# END
