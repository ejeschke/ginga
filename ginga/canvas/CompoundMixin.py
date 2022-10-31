#
# CompoundMixin.py -- enable compound capabilities.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from functools import reduce
import warnings

import numpy as np

__all__ = ['CompoundMixin']


class CompoundMixin(object):
    """A CompoundMixin is a mixin class that makes an object that is an
    aggregation of other objects.

    It is used to make generic compound drawing types as well as (for example)
    layers of canvases on top of an image.
    """

    def __init__(self):
        # holds a list of objects to be drawn
        self.objects = []
        if not hasattr(self, 'crdmap'):
            self.crdmap = None
        if not hasattr(self, 'coord'):
            self.coord = None
        self.opaque = False
        self._contains_reduce = np.logical_or

    def __contains__(self, key):
        return key in self.objects

    def get_llur(self):
        """
        Get lower-left and upper-right coordinates of the bounding box
        of this compound object.

        Returns
        -------
        x1, y1, x2, y2: a 4-tuple of the lower-left and upper-right coords
        """
        points = np.array([obj.get_llur() for obj in self.objects])
        t_ = points.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[2].max(), t_[3].max()
        return (x1, y1, x2, y2)

    def contains_pts(self, pts):
        if len(self.objects) == 0:
            x_arr, y_arr = np.asarray(pts).T
            return np.full(x_arr.shape, False, dtype=np.bool)

        return reduce(self._contains_reduce,
                      map(lambda obj: obj.contains_pts(pts), self.objects))

    def get_items_at(self, pt):
        res = []
        for obj in self.objects:
            if obj.is_compound() and not obj.opaque:
                # non-opaque compound object, list up compatible members
                res.extend(obj.get_items_at(pt))
            elif obj.contains_pt(pt):
                #res.insert(0, obj)
                res.append(obj)
        return res

    def get_objects_by_kind(self, kind):
        return filter(lambda obj: obj.kind == kind, self.objects)

    def get_objects_by_kinds(self, kinds):
        return filter(lambda obj: obj.kind in kinds, self.objects)

    def select_contains_pt(self, viewer, pt):
        for obj in self.objects:
            if obj.select_contains_pt(viewer, pt):
                return True
        return False

    def select_items_at(self, viewer, pt, test=None):
        res = []
        try:
            for obj in self.objects:
                if obj.is_compound() and not obj.opaque:
                    # non-opaque compound object, list up compatible members
                    res.extend(obj.select_items_at(viewer, pt, test=test))

                is_inside = obj.select_contains_pt(viewer, pt)
                if test is None:
                    if is_inside:
                        res.append(obj)
                elif test(obj, pt, is_inside):
                    # custom test
                    res.append(obj)
        except Exception as e:
            self.logger.error("error selecting object(s): {}".format(e),
                              exc_info=True)
            res = []
        return res

    def initialize(self, canvas, viewer, logger):
        super().initialize(canvas, viewer, logger)

        # initialize children
        for obj in self.objects:
            obj.initialize(self, viewer, logger)

    def inherit_from(self, obj):
        self.crdmap = obj.crdmap
        self.logger = obj.logger
        self.viewer = obj.viewer

    def is_compound(self):
        return True

    def use_coordmap(self, mapobj):
        super().use_coordmap(mapobj)

        for obj in self.objects:
            obj.use_coordmap(mapobj)

    def draw(self, viewer):
        for obj in self.objects:
            obj.draw(viewer)

    def get_objects(self):
        return self.objects

    def has_object(self, obj):
        return obj in self.objects

    def copy(self, share=[]):
        obj = super().copy(share=share)
        obj.objects = [obj.copy(share=share) for obj in self.objects]
        return obj

    def delete_object(self, obj):
        self.objects.remove(obj)

    def delete_objects(self, objects):
        for obj in objects:
            self.delete_object(obj)

    def delete_all_objects(self):
        self.objects[:] = []

    def roll_objects(self, n):
        num = len(self.objects)
        if num == 0:
            return
        n = n % num
        self.objects = self.objects[-n:] + self.objects[:-n]

    def swap_objects(self):
        num = len(self.objects)
        if num >= 2:
            l = self.objects
            self.objects = l[:num - 2] + [l[num - 1], l[num - 2]]

    def set_attr_all(self, **kwdargs):
        for obj in self.objects:
            for attrname, val in kwdargs.items():
                if hasattr(obj, attrname):
                    setattr(obj, attrname, val)

    def add_object(self, obj, belowThis=None):

        obj.initialize(self, self.viewer, self.logger)

        if belowThis is None:
            self.objects.append(obj)
        else:
            index = self.objects.index(belowThis)
            self.objects.insert(index, obj)

    def raise_object(self, obj, aboveThis=None):
        if aboveThis is None:
            # no reference object--move to top
            self.objects.remove(obj)
            self.objects.append(obj)
        else:
            # Force an error if the reference object doesn't exist in list
            index = self.objects.index(aboveThis)
            self.objects.remove(obj)
            index = self.objects.index(aboveThis)
            self.objects.insert(index + 1, obj)

    def lower_object(self, obj, belowThis=None):
        if belowThis is None:
            # no reference object--move to bottom
            self.objects.remove(obj)
            self.objects.insert(0, obj)
        else:
            # Force an error if the reference object doesn't exist in list
            index = self.objects.index(belowThis)
            self.objects.remove(obj)
            index = self.objects.index(belowThis)
            self.objects.insert(index, obj)

    def rotate(self, theta, xoff=0, yoff=0):
        warnings.warn("rotate(theta_deg) has been deprecated--"
                      "use rotate_deg([theta_deg]) instead",
                      DeprecationWarning)
        self.rotate_deg([theta], (xoff, yoff))

    def rotate_deg(self, thetas, offset):
        for obj in self.objects:
            obj.rotate_deg(thetas, offset)

    def move_delta_pt(self, off_pt):
        for obj in self.objects:
            obj.move_delta_pt(off_pt)

    def scale_by_factors(self, factors):
        for obj in self.objects:
            obj.scale_by_factors(factors)

    def get_reference_pt(self):
        # Reference point for a compound object is the average of all
        # it's contituents reference points
        points = np.asarray([obj.get_reference_pt()
                             for obj in self.objects])
        t_ = points.T
        x, y = np.average(t_[0]), np.average(t_[1])
        return (x, y)

    get_center_pt = get_reference_pt

    def get_points(self):
        res = []
        for obj in self.objects:
            res.extend(list(obj.get_points()))
        return res

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        # currently only move_pt is supported for compound objects
        return [move_pt]

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            # move control point
            ctr_x, ctr_y = self.get_reference_pt()
            delta_pt = (pt[0] - ctr_x, pt[1] - ctr_y)
            self.move_delta_pt(delta_pt)
        else:
            raise ValueError("No point corresponding to index %d" % (i))
