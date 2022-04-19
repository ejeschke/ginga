#
# CanvasObject.py -- base class for shapes drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np
from collections import namedtuple
import copy

from ginga.misc import Callback, Bunch
from ginga import trcalc, colors

from . import coordmap

__all__ = ['CanvasObjectBase', 'get_canvas_type', 'get_canvas_types',
           'register_canvas_type', 'register_canvas_types']

colors_plus_none = [None] + colors.get_colors()

coord_names = ['data', 'wcs', 'cartesian', 'percentage', 'window']

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
    is an item that can be placed on a Ginga canvas.

    This class defines common methods used by all such objects.
    """

    def __init__(self, **kwdargs):
        if not hasattr(self, 'cb'):
            Callback.Callbacks.__init__(self)
        self.cap = 'ball'
        self.cap_radius = 4
        self.editable = True
        self.pickable = False
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
                     'pick-hover', 'pick-enter', 'pick-leave',
                     'pick-key'):
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
            raise CanvasObjectError(
                "method get_data() takes at most 2 arguments")

    def use_coordmap(self, mapobj):
        self.crdmap = mapobj

    def canvascoords(self, viewer, data_x, data_y, center=None):
        if center is not None:
            self.logger.warn(
                "`center` keyword is ignored and will be deprecated")

        return viewer.get_canvas_xy(data_x, data_y)

    def is_compound(self):
        return False

    def copy(self, share=[]):
        obj = copy.copy(self)
        obj.viewer = None
        if 'data' not in share:
            obj.data = None
        return obj

    def contains_pts(self, points):
        contains = np.asarray([False] * len(points))
        return contains

    def contains_pt(self, pt):
        pts = np.asarray([pt])
        return self.contains_pts(pts)[0]

    def select_contains_pt(self, viewer, pt):
        return self.contains_pt(pt)

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calc_vertexes(x1, y1, x2, y2)

        alpha = getattr(self, 'alpha', 1.0)
        cr.set_fill(self.color, alpha=alpha)
        cr.draw_polygon(((x2, y2), (i1, j1), (i2, j2)))
        cr.set_fill(None)

    def draw_caps(self, cr, cap, points, radius=None):
        i = 0
        for pt in points:
            cx, cy = pt[:2]
            if radius is None:
                radius = self.cap_radius
            alpha = getattr(self, 'alpha', 1.0)
            if cap == 'ball':
                color = self.color
                # Draw edit control points in different colors than the others
                if isinstance(pt, EditPoint):
                    cr.set_fill('black', alpha=alpha)
                    r = cr.renderer.calc_const_len(radius + 2.0)
                    cr.draw_circle(cx, cy, r)

                    color = pt.edit_color

                cr.set_fill(color, alpha=alpha)
                r = cr.renderer.calc_const_len(radius)
                cr.draw_circle(cx, cy, r)
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

        cpoints = tuple([_map_cpt(points[i], cpoints[i])
                         for i in range(len(points))])
        self.draw_caps(cr, 'ball', cpoints)

    def calc_radius(self, viewer, p1, p2):
        x1, y1 = p1[:2]
        x2, y2 = p2[:2]
        # TODO: the accuracy of this calculation of radius might be improved?
        radius = np.sqrt(abs(y2 - y1)**2 + abs(x2 - x1)**2)
        return (x1, y1, radius)

    def calc_vertexes(self, start_cx, start_cy, end_cx, end_cy,
                      arrow_length=10, arrow_degrees=0.35):

        angle = np.arctan2(end_cy - start_cy, end_cx - start_cx) + np.pi

        cx1 = end_cx + arrow_length * np.cos(angle - arrow_degrees)
        cy1 = end_cy + arrow_length * np.sin(angle - arrow_degrees)
        cx2 = end_cx + arrow_length * np.cos(angle + arrow_degrees)
        cy2 = end_cy + arrow_length * np.sin(angle + arrow_degrees)

        return (cx1, cy1, cx2, cy2)

    def swapxy(self, x1, y1, x2, y2):
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return (x1, y1, x2, y2)

    def scale_font(self, viewer):
        scale = viewer.get_scale_max()
        basesize = getattr(self, 'fontsize', 10.0)
        if basesize is None:
            basesize = 10.0
        min_size = getattr(self, 'fontsize_min', 2.0)
        n = 1.4
        fontsize = max(min_size, basesize + np.log(scale) / np.log(n))
        max_size = getattr(self, 'fontsize_max', None)
        if max_size is not None:
            fontsize = min(max_size, fontsize)
        return fontsize

    def get_points(self):
        """Get the set of points that is used to draw the object.

        Points are returned in *data* coordinates.
        """
        if hasattr(self, 'points'):
            points = self.crdmap.to_data(self.points)
        else:
            points = []
        return points

    def get_data_points(self, points=None):
        """Points returned are in data coordinates."""
        if points is None:
            points = self.points
        points = self.crdmap.to_data(points)
        return points

    def set_data_points(self, points):
        """
        Input `points` must be in data coordinates, will be converted
        to the coordinate space of the object and stored.
        """
        self.points = np.asarray(self.crdmap.data_to(points))

    def rotate_deg(self, thetas, offset):
        points = np.asarray(self.get_data_points(), dtype=np.double)
        points = trcalc.rotate_coord(points, thetas, offset)
        self.set_data_points(points)

    def rotate_by_deg(self, thetas):
        ref_pt = self.get_reference_pt()
        self.rotate_deg(thetas, ref_pt)

    def rerotate_by_deg(self, thetas, detail):
        ref_pt = detail.center_pos
        points = np.asarray(detail.points, dtype=np.double)
        points = trcalc.rotate_coord(points, thetas, ref_pt)
        self.set_data_points(points)

    def move_delta_pt(self, off_pt):
        points = np.asarray(self.get_data_points(), dtype=np.double)
        points = np.add(points, off_pt)
        self.set_data_points(points)

    def move_to_pt(self, dst_pt):
        ref_pt = self.get_reference_pt()
        off_pt = np.subtract(dst_pt, ref_pt)
        self.move_delta_pt(off_pt)

    def get_num_points(self):
        return(len(self.points))

    def set_point_by_index(self, i, pt):
        #self.points[i] = self.crdmap.data_to(pt)
        # Can we eventually use something like the above?
        points = np.asarray(self.points, dtype=float)
        points[i] = self.crdmap.data_to(pt)
        self.points = points

    def get_point_by_index(self, i):
        return self.crdmap.to_data(self.points[i])

    def scale_by_factors(self, factors):
        ctr_pt = self.get_center_pt()
        pts = np.asarray(self.get_data_points(), dtype=np.double)
        pts = np.add(np.multiply(np.subtract(pts, ctr_pt), factors), ctr_pt)
        self.set_data_points(pts)

    def rescale_by_factors(self, factors, detail):
        ctr_pt = detail.center_pos
        pts = np.asarray(detail.points, dtype=np.double)
        pts = np.add(np.multiply(np.subtract(pts, ctr_pt), factors), ctr_pt)
        self.set_data_points(pts)

    def setup_edit(self, detail):
        """subclass should override as necessary."""
        detail.center_pos = self.get_center_pt()

    def calc_rotation_from_pt(self, pt, detail):
        x, y = pt[:2]
        ctr_x, ctr_y = detail.center_pos[:2]
        start_x, start_y = detail.start_pos[:2]
        # calc angle of starting point wrt origin
        deg1 = np.degrees(np.arctan2(start_y - ctr_y,
                                     start_x - ctr_x))
        # calc angle of current point wrt origin
        deg2 = np.degrees(np.arctan2(y - ctr_y, x - ctr_x))
        delta_deg = deg2 - deg1
        return delta_deg

    def calc_scale_from_pt(self, pt, detail):
        x, y = pt[:2]
        ctr_x, ctr_y = detail.center_pos[:2]
        start_x, start_y = detail.start_pos[:2]
        dx, dy = start_x - ctr_x, start_y - ctr_y
        # calc distance of starting point wrt origin
        dist1 = np.sqrt(dx**2.0 + dy**2.0)
        dx, dy = x - ctr_x, y - ctr_y
        # calc distance of current point wrt origin
        dist2 = np.sqrt(dx**2.0 + dy**2.0)
        scale_f = dist2 / dist1
        return scale_f

    def calc_dual_scale_from_pt(self, pt, detail):
        x, y = pt[:2]
        ctr_x, ctr_y = detail.center_pos[:2]
        start_x, start_y = detail.start_pos[:2]
        # calc distance of starting point wrt origin
        dx, dy = start_x - ctr_x, start_y - ctr_y
        # calc distance of current point wrt origin
        ex, ey = x - ctr_x, y - ctr_y
        scale_x, scale_y = float(ex) / dx, float(ey) / dy
        return scale_x, scale_y

    def convert_mapper(self, tomap):
        """
        Converts our object from using one coordinate map to another.

        NOTE: In some cases this only approximately preserves the
        equivalent point values when transforming between coordinate
        spaces.
        """
        frommap = self.crdmap
        if frommap == tomap:
            return

        # mild hack to convert radii on objects that have them
        if hasattr(self, 'radius'):
            # get coordinates of a point radius away from center
            # under current coordmap
            x0, y0 = frommap.offset_pt((self.x, self.y), (self.radius, 0))
            pts = frommap.to_data(((self.x, self.y), (x0, y0)))
            pts = tomap.data_to(pts)
            self.radius = np.fabs(pts[1][0] - pts[0][0])

        elif hasattr(self, 'xradius'):
            # similar to above case, but there are 2 radii
            x0, y0 = frommap.offset_pt((self.x, self.y), (self.xradius,
                                                          self.yradius))
            pts = frommap.to_data(((self.x, self.y), (x0, y0)))
            pts = tomap.data_to(pts)
            self.xradius = np.fabs(pts[1][0] - pts[0][0])
            self.yradius = np.fabs(pts[1][1] - pts[0][1])

        # mild hack to convert width on objects that have them
        if hasattr(self, 'width'):
            # get coordinates of a point 'width' unit away from center
            # under current coordmap
            x0, y0 = frommap.offset_pt((self.x, self.y), (self.width, 0))
            pts = frommap.to_data(((self.x, self.y), (x0, y0)))
            pts = tomap.data_to(pts)
            self.width = np.fabs(pts[1][0] - pts[0][0])

        elif hasattr(self, 'xwidth'):
            # similar to above case, but there are 2 widths, for X and Y
            x0, y0 = frommap.offset_pt((self.x, self.y), (self.xwidth,
                                                          self.ywidth))
            pts = frommap.to_data(((self.x, self.y), (x0, y0)))
            pts = tomap.data_to(pts)
            self.xwidth = np.fabs(pts[1][0] - pts[0][0])
            self.ywidth = np.fabs(pts[1][1] - pts[0][1])

        data_pts = self.get_data_points()

        # set our map to the new map
        self.crdmap = tomap

        self.set_data_points(data_pts)

    def point_within_radius(self, points, pt, canvas_radius,
                            scales=(1.0, 1.0)):
        """Points `points` and point `pt` are in data coordinates.
        Return True for points within the circle defined by
        a center at point `pt` and within canvas_radius.
        """
        scale_x, scale_y = scales
        x, y = pt
        a_arr, b_arr = np.asarray(points).T
        dx = np.fabs(x - a_arr) * scale_x
        dy = np.fabs(y - b_arr) * scale_y
        new_radius = np.sqrt(dx**2 + dy**2)
        res = (new_radius <= canvas_radius)
        return res

    def within_radius(self, viewer, points, pt, canvas_radius):
        """Points `points` and point `pt` are in data coordinates.
        Return True for points within the circle defined by
        a center at point `pt` and within canvas_radius.
        The distance between points is scaled by the canvas scale.
        """
        scales = viewer.get_scale_xy()
        return self.point_within_radius(points, pt, canvas_radius,
                                        scales)

    def get_pt(self, viewer, points, pt, canvas_radius=None):
        """Takes an array of points `points` and a target point `pt`.
        Returns the first index of the point that is within the
        radius of the target point.  If none of the points are within
        the radius, returns None.
        """
        if canvas_radius is None:
            canvas_radius = self.cap_radius

        if hasattr(self, 'rot_deg'):
            # rotate point back to cartesian alignment for test
            ctr_pt = self.get_center_pt()
            pt = trcalc.rotate_coord(pt, [-self.rot_deg], ctr_pt)

        res = self.within_radius(viewer, points, pt, canvas_radius)
        return np.flatnonzero(res)

    def point_within_line(self, points, p_start, p_stop, canvas_radius):
        # TODO: is there an algorithm with the cross and dot products
        # that is more efficient?
        r = canvas_radius
        x1, y1 = p_start
        x2, y2 = p_stop
        xmin, xmax = min(x1, x2) - r, max(x1, x2) + r
        ymin, ymax = min(y1, y2) - r, max(y1, y2) + r
        div = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        a_arr, b_arr = np.asarray(points).T
        d = np.fabs((x2 - x1) * (y1 - b_arr) - (x1 - a_arr) * (y2 - y1)) / div

        contains = np.logical_and(
            np.logical_and(xmin <= a_arr, a_arr <= xmax),
            np.logical_and(d <= canvas_radius,
                           np.logical_and(ymin <= b_arr, b_arr <= ymax)))
        return contains

    def within_line(self, viewer, points, p_start, p_stop, canvas_radius):
        """Points `points` and line endpoints `p_start`, `p_stop` are in
        data coordinates.
        Return True for points within the line defined by a line from
        p_start to p_end and within `canvas_radius`.
        The distance between points is scaled by the viewer's canvas scale.
        """
        scale_x, scale_y = viewer.get_scale_xy()
        new_radius = canvas_radius * 1.0 / min(scale_x, scale_y)

        return self.point_within_line(points, p_start, p_stop, new_radius)

    def get_center_pt(self):
        """Return the geometric average of points as data_points.
        """
        P = np.asarray(self.get_data_points(), dtype=np.double)
        x = P[:, 0]
        y = P[:, 1]
        ctr_x = np.sum(x) / float(len(x))
        ctr_y = np.sum(y) / float(len(y))
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
        # If points are passed, they are assumed to be in data space
        if points is None:
            points = self.get_points()

        if (not no_rotate) and hasattr(self, 'rot_deg') and self.rot_deg != 0.0:
            # rotate vertices according to rotation
            ctr_x, ctr_y = self.get_center_pt()
            points = trcalc.rotate_coord(points, [self.rot_deg], (ctr_x, ctr_y))

        crdmap = viewer.get_coordmap('native')
        return crdmap.data_to(points)

    def get_bbox(self, points=None):
        """
        Get bounding box of this object.

        Returns
        -------
        (p1, p2, p3, p4): a 4-tuple of the points in data coordinates,
        beginning with the lower-left and proceeding counter-clockwise.
        """
        if points is None:
            x1, y1, x2, y2 = self.get_llur()
            return ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
        else:
            return trcalc.strip_z(trcalc.get_bounds(points))

    def get_llur(self):
        a, b = trcalc.get_bounds(self.get_data_points())
        return (a[0], a[1], b[0], b[1])

    # --- TO BE DEPRECATED METHODS ---

    def move_delta(self, xoff, yoff):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use move_delta_pt instead.
        """
        self.move_delta_pt((xoff, yoff))

    def move_to(self, xdst, ydst):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use move_to_pt() instead.
        """
        self.move_to_pt((xdst, ydst))

    def scale_by(self, scale_x, scale_y):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use scale_by_factors() instead.
        """
        self.scale_by_factors((scale_x, scale_y))

    def rescale_by(self, scale_x, scale_y, detail):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use rescale_by_factors() instead.
        """
        self.rescale_by_factors((scale_x, scale_y), detail)

    def rotate(self, theta_deg, xoff=0, yoff=0):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use rotate_deg() instead.
        """
        self.rotate_deg([theta_deg], (xoff, yoff))

    def rotate_by(self, theta_deg):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use rotate_by_deg() instead.
        """
        self.rotate_by_deg([theta_deg])

    def contains_arr(self, x_arr, y_arr):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use contains_pts() instead.
        """
        pts = np.asarray((x_arr, y_arr)).T
        return self.contains_pts(pts)

    def contains(self, x, y):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use contains_pt() instead.
        """
        return self.contains_pt((x, y))

    def select_contains(self, viewer, x, y):
        """For backward compatibility.  TO BE DEPRECATED--DO NOT USE.
        Use select_contains_pt() instead.
        """
        return self.select_contains_pt(viewer, (x, y))


# this is the data structure to which drawing classes are registered
drawCatalog = Bunch.Bunch(caseless=True)


def get_canvas_types():
    # force registration of all canvas types
    import ginga.canvas.types.all  # noqa

    return drawCatalog


def get_canvas_type(name):
    # force registration of all canvas types
    import ginga.canvas.types.all  # noqa

    return drawCatalog[name]


def register_canvas_type(name, klass):
    global drawCatalog
    drawCatalog[name] = klass


def register_canvas_types(klass_dict):
    global drawCatalog
    drawCatalog.update(klass_dict)


# funky boolean converter
_bool = lambda st: str(st).lower() == 'true'  # noqa

# color converter
_color = lambda name: name  # noqa

# END
