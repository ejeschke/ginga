#
# CanvasObject.py -- base class for shapes drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy
from collections import namedtuple

from ginga.misc import Callback, Bunch
from ginga import trcalc, colors
from ginga.util.six.moves import map

from . import coordmap

__all__ = ['CanvasObjectBase', 'get_canvas_type', 'get_canvas_types',
           'register_canvas_type', 'register_canvas_types']

colors_plus_none = [ None ] + colors.get_colors()

Point = namedtuple('Point', ['x', 'y'])

class EditPoint(Point):
    edit_color = 'yellow'
class MovePoint(EditPoint):
    edit_color = 'orangered'
class ScalePoint(EditPoint):
    edit_color = 'green'
class RotatePoint(EditPoint):
    edit_color = 'skyblue'

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
        self.crdmap = None
        self.tag = None
        if not hasattr(self, 'kind'):
            self.kind = None
        # For debugging
        self.name = None
        self.viewer = None

        # For callbacks
        for name in ('edited', 'pick-down', 'pick-move', 'pick-up',
                     'pick-hover', 'pick-enter', 'pick-leave'):
            self.enable_callback(name)

    def initialize(self, canvas, viewer, logger):
        self.viewer = viewer
        self.logger = logger
        if self.crdmap is None:
            if self.coord is None:
                # default mapping is to data coordinates
                self.coord = 'data'

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

    def canvascoords(self, viewer, data_x, data_y, center=None):
        if center is not None:
            self.logger.warn("`center` keyword is ignored and will be deprecated")

        return viewer.get_canvas_xy(data_x, data_y)

    def is_compound(self):
        return False

    def contains_arr(self, x_arr, y_arr):
        contains = numpy.asarray([False] * len(x_arr))
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

    def draw_caps(self, cr, cap, points, radius=None):
        i = 0
        for pt in points:
            cx, cy = pt
            if radius is None:
                radius = self.cap_radius
            alpha = getattr(self, 'alpha', 1.0)
            if cap == 'ball':
                color = self.color
                # Draw edit control points in different colors than the others
                if isinstance(pt, EditPoint):
                    cr.set_fill('black', alpha=alpha)
                    cr.draw_circle(cx, cy, radius+2.0)

                    color = pt.edit_color

                cr.set_fill(color, alpha=alpha)
                cr.draw_circle(cx, cy, radius)
                #cr.set_fill(self, None)
            i += 1

    def draw_edit(self, cr, viewer):
        bbox = self.get_bbox()
        cpoints = self.get_cpoints(viewer, points=bbox, no_rotate=True)
        cr.set_fill(None)
        cr.set_line(color='cyan', style='dash')
        cr.draw_polygon(cpoints)

        points = self.get_edit_points(viewer)
        cpoints = self.get_cpoints(viewer, points=points)
        # preserve point types for coloring
        def _map_cpt(pt, cpt):
            if isinstance(pt, EditPoint):
                return pt.__class__(*cpt)
            return cpt

        cpoints = tuple([ _map_cpt(points[i], cpoints[i])
                    for i in range(len(points)) ])
        self.draw_caps(cr, 'ball', cpoints)

    def calc_radius(self, viewer, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        # TODO: the accuracy of this calculation of radius might be improved?
        radius = math.sqrt(abs(y2 - y1)**2 + abs(x2 - x1)**2)
        return (x1, y1, radius)

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

    def get_points(self):
        """Get the set of points that is used to draw the object.

        Points are returned in *data* coordinates.
        """
        points = list(map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                          self.points))
        return points

    def get_data_points(self, points=None):
        if points is None:
            points = self.points
        points = list(map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                          points))
        return points

    def set_data_points(self, points):
        points = list(map(lambda pt: self.crdmap.data_to(pt[0], pt[1]),
                          points))
        self.points = points

    def rotate(self, theta_deg, xoff=0, yoff=0):
        points = numpy.asarray(self.get_data_points(), dtype=numpy.double)
        points = trcalc.rotate_coord(points, theta_deg, [xoff, yoff])
        self.set_data_points(points)

    def rotate_by(self, theta_deg):
        ref_x, ref_y = self.get_reference_pt()
        self.rotate(theta_deg, xoff=ref_x, yoff=ref_y)

    def rerotate_by(self, theta_deg, detail):
        ref_x, ref_y = detail.center_pos
        points = numpy.asarray(detail.points, dtype=numpy.double)
        points = trcalc.rotate_coord(points, theta_deg, [ref_x, ref_y])
        self.set_data_points(points)

    def move_delta(self, xoff, yoff):
        ## self.points = list(map(
        ##     lambda pt: self.crdmap.offset_pt(pt, xoff, yoff),
        ##     self.points))
        points = numpy.asarray(self.get_data_points(), dtype=numpy.double)
        points.T[0] += xoff
        points.T[1] += yoff
        self.set_data_points(points)

    def move_to(self, xdst, ydst):
        x, y = self.get_reference_pt()
        return self.move_delta(xdst - x, ydst - y)

    def get_num_points(self):
        return(len(self.points))

    def set_point_by_index(self, i, pt):
        points = self.get_data_points()
        points[i] = pt
        self.set_data_points(points)

    def get_point_by_index(self, i):
        points = self.get_data_points()
        return points[i]

    def scale_by(self, scale_x, scale_y):
        ctr_x, ctr_y = self.get_center_pt()
        pts = numpy.asarray(self.get_data_points(), dtype=numpy.double)
        pts[:, 0] = (pts[:, 0] - ctr_x) * scale_x + ctr_x
        pts[:, 1] = (pts[:, 1] - ctr_y) * scale_y + ctr_y
        self.set_data_points(pts)

    def rescale_by(self, scale_x, scale_y, detail):
        ctr_x, ctr_y = detail.center_pos
        pts = numpy.asarray(detail.points, dtype=numpy.double)
        pts[:, 0] = (pts[:, 0] - ctr_x) * scale_x + ctr_x
        pts[:, 1] = (pts[:, 1] - ctr_y) * scale_y + ctr_y
        self.set_data_points(pts)

    def setup_edit(self, detail):
        """subclass should override as necessary."""
        detail.center_pos = self.get_center_pt()

    def calc_rotation_from_pt(self, pt, detail):
        x, y = pt
        ctr_x, ctr_y = detail.center_pos
        start_x, start_y = detail.start_pos
        # calc angle of starting point wrt origin
        deg1 = math.degrees(math.atan2(start_y - ctr_y,
                                       start_x - ctr_x))
        # calc angle of current point wrt origin
        deg2 = math.degrees(math.atan2(y - ctr_y, x - ctr_x))
        delta_deg = deg2 - deg1
        return delta_deg

    def calc_scale_from_pt(self, pt, detail):
        x, y = pt
        ctr_x, ctr_y = detail.center_pos
        start_x, start_y = detail.start_pos
        dx, dy = start_x - ctr_x, start_y - ctr_y
        # calc distance of starting point wrt origin
        dist1 = math.sqrt(dx**2.0 + dy**2.0)
        dx, dy = x - ctr_x, y - ctr_y
        # calc distance of current point wrt origin
        dist2 = math.sqrt(dx**2.0 + dy**2.0)
        scale_f = dist2 / dist1
        return scale_f

    def calc_dual_scale_from_pt(self, pt, detail):
        x, y = pt
        ctr_x, ctr_y = detail.center_pos
        start_x, start_y = detail.start_pos
        # calc distance of starting point wrt origin
        dx, dy = start_x - ctr_x, start_y - ctr_y
        # calc distance of current point wrt origin
        ex, ey = x - ctr_x, y - ctr_y
        scale_x, scale_y = float(ex) / dx, float(ey) / dy
        return scale_x, scale_y

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
            ctr_x, ctr_y = self.get_center_pt()
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

    def get_center_pt(self):
        """Return the geometric average of points as data_points.
        """
        P = numpy.asarray(self.get_data_points(), dtype=numpy.double)
        x = P[:, 0]
        y = P[:, 1]
        ctr_x = numpy.sum(x) / float(len(x))
        ctr_y = numpy.sum(y) / float(len(y))
        return ctr_x, ctr_y

    def get_reference_pt(self):
        return self.get_center_pt()

    def get_move_scale_rotate_pts(self, viewer):
        """Returns 3 edit control points for editing this object: a move
        point, a scale point and a rotate point.  These points are all in
        data coordinates.
        """
        scale = viewer.get_scale_min()
        ref_x, ref_y = self.get_center_pt()
        xl, yl, xu, yu = self.get_llur()
        offset = 8.0 / scale
        scl_x, scl_y = xl - offset, yl - offset
        rot_x, rot_y = xu + offset, yu + offset
        if hasattr(self, 'rot_deg'):
            # if this is an object with a rotation attribute, pre rotate
            # the control points in the opposite direction, because they
            # will be rotated back
            theta = -self.rot_deg
            scl_x, scl_y = trcalc.rotate_pt(scl_x, scl_y, theta,
                                            xoff=ref_x, yoff=ref_y)
            rot_x, rot_y = trcalc.rotate_pt(rot_x, rot_y, theta,
                                            xoff=ref_x, yoff=ref_y)
        move_pt = MovePoint(ref_x, ref_y)
        scale_pt = ScalePoint(scl_x, scl_y)
        rotate_pt = RotatePoint(rot_x, rot_y)

        return (move_pt, scale_pt, rotate_pt)

    def get_cpoints(self, viewer, points=None, no_rotate=False):
        if points is None:
            points = self.get_points()

        points = numpy.asarray(points)

        if (not no_rotate) and hasattr(self, 'rot_deg') and self.rot_deg != 0.0:
            # rotate vertices according to rotation
            ctr_x, ctr_y = self.get_center_pt()
            points = trcalc.rotate_coord(points, self.rot_deg, (ctr_x, ctr_y))

        cpoints = tuple(map(lambda p: self.canvascoords(viewer, p[0], p[1]),
                            points))
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
