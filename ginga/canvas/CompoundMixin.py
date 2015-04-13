#
# CompoundMixin.py -- enable compound capabilities.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, traceback
import numpy

from ginga.util.six.moves import map, zip, reduce

class CompoundMixin(object):
    """A CompoundMixin makes an object that is an aggregation of other objects.
    It is used to make generic compound drawing types as well as (for example)
    layers of canvases on top of an image.
    """

    def __init__(self):
        # holds a list of objects to be drawn
        self.objects = []
        self._contains_reduce = numpy.logical_or

    def get_llur(self):
        points = numpy.array(list(map(lambda obj: obj.get_llur(),
                                      self.objects)))
        t_ = points.T
        x1, y1 = min(t_[0].min(), t_[0].min()), min(t_[1].min(), t_[3].min())
        x2, y2 = max(t_[0].max(), t_[0].max()), min(t_[1].max(), t_[3].max())
        return (x1, y1, x2, y2)

    def get_edit_points(self):
        x1, y1, x2, y2 = self.get_llur()
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def contains_arr(self, x_arr, y_arr):
        return reduce(self._contains_reduce,
                      map(lambda obj: obj.contains_arr(x_arr, y_arr)))

    def contains(self, x, y):
        for obj in self.objects:
            if obj.contains(x, y):
                return True
        return False

    def getItemsAt(self, x, y):
        res = []
        for obj in self.objects:
            if obj.contains(x, y):
                #res.insert(0, obj)
                res.append(obj)
        return res
        
    def select_contains(self, x, y):
        for obj in self.objects:
            if obj.select_contains(x, y):
                return True
        return False

    def select_items_at(self, x, y, test=None):
        res = []
        try:
            for obj in self.objects:
                if obj.is_compound():
                    # compound object, list up compatible members
                    res.extend(obj.select_items_at(x, y, test=test))
                    continue

                is_inside = obj.select_contains(x, y)
                if test is None:
                    if is_inside:
                        res.append(obj)
                elif test(obj, x, y, is_inside):
                    # custom test
                    res.append(obj)
        except Exception as e:
            print("error selecting objects: %s" % (str(e)))
            try:
                # log traceback, if possible
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
            except Exception:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)
            res = []
        return res
        
    def initialize(self, tag, viewer, logger):
        #self.tag = tag
        self.viewer = viewer
        self.logger = logger

        # TODO: subtags for objects?
        for obj in self.objects:
            obj.initialize(None, viewer, logger)

    def inherit_from(self, obj):
        self.crdmap = obj.crdmap
        self.logger = obj.logger
        self.viewer = obj.viewer
        
    def is_compound(self):
        return True
    
    def use_coordmap(self, mapobj):
        for obj in self.objects:
            obj.use_coordmap(mapobj)

    def draw(self):
        for obj in self.objects:
            obj.draw()

    def getObjects(self):
        return self.objects
    
    def deleteObject(self, obj):
        self.objects.remove(obj)
        
    def deleteObjects(self, objects):
        for obj in objects:
            self.deleteObject(obj)
        
    def deleteAllObjects(self):
        self.objects = []

    def setAttrAll(self, **kwdargs):
        for obj in self.objects:
            for attrname, val in kwdargs.items():
                if hasattr(obj, attrname):
                    setattr(obj, attrname, val)
        
    def addObject(self, obj, belowThis=None):
        obj.initialize(None, self.viewer, self.logger)
        obj.viewer = self.viewer
        if not belowThis:
            self.objects.append(obj)
        else:
            index = self.objects.index(belowThis)
            self.objects.insert(index, obj)
        
    def raiseObject(self, obj, aboveThis=None):
        if not aboveThis:
            # no reference object--move to top
            self.objects.remove(obj)
            self.objects.append(obj)
        else:
            # Force an error if the reference object doesn't exist in list
            index = self.objects.index(aboveThis)
            self.objects.remove(obj)
            index = self.objects.index(aboveThis)
            self.objects.insert(index+1, obj)

    def lowerObject(self, obj, belowThis=None):
        if not belowThis:
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
        for obj in self.objects:
            obj.rotate(theta, xoff=xoff, yoff=yoff)
            
    def move_delta(self, xoff, yoff):
        for obj in self.objects:
            obj.move_delta(xoff, yoff)

    def rotate_by(self, theta_deg):
        ref_x, ref_y = self.get_reference_pt()
        for obj in self.objects:
            self.rotate(theta_deg, xoff=ref_x, yoff=ref_y)
    
    def scale_by(self, scale_x, scale_y):
        for obj in self.objects:
            obj.scale_by(scale_x, scale_y)

    def get_reference_pt(self):
        # Reference point for a compound object is the average of all
        # it's contituents reference points
        points = numpy.array([ obj.get_reference_pt() for obj in self.objects ])
        t_ = points.T
        x, y = numpy.average(t_[0]), numpy.average(t_[1])
        return (x, y)

    def move_to(self, xdst, ydst):
        x, y = self.get_reference_pt()
        for obj in self.objects:
            obj.move_delta(xdst - x, ydst - y)

    def reorder_layers(self):
        self.objects.sort(key=lambda obj: getattr(obj, '_zorder', 0))
        for obj in self.objects:
            if obj.is_compound():
                obj.reorder_layers()

    def get_points(self):
        res = []
        for obj in self.objects:
            res.extend(list(obj.get_points()))
        return res
    
    def set_edit(self, tf):
        for obj in self.objects:
            try:
                obj.set_edit(tf)
            except ValueError:
                # TODO: should check for specific node-can't edit error
                continue
        

#END
