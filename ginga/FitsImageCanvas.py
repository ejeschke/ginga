#!/usr/bin/env python
#
# FitsImageCanvas.py -- Abstract base classes for FitsImageCanvas{Gtk,Qt}.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import time

from ginga.misc import Bunch

class CanvasObjectError(Exception):
    pass

class CanvasObjectBase(object):
    """This is the abstract base class for a CanvasObject.  A CanvasObject
    is an item that can be placed on a FitsImageCanvas.

    This class defines common methods used by all such objects.
    """

    def __init__(self, **kwdargs):
        self.__dict__.update(kwdargs)
        self.data = None

    def initialize(self, tag, fitsimage, logger):
        self.tag = tag
        self.fitsimage = fitsimage
        self.logger = logger

    def set_data(self, **kwdargs):
        if self.data == None:
            self.data = Bunch.Bunch(kwdargs)
        else:
            self.data.update(kwdargs)
            
    def get_data(self):
        return self.data

    def redraw(self, whence=3):
        self.fitsimage.redraw(whence=whence)
        
    def canvascoords(self, x, y, center=True):
        a, b = self.fitsimage.canvascoords(x, y, center=center)
        return (a, b)

    def isCompound(self):
        return False
    
    def contains(self, x, y):
        return False
    
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
        zoomlevel = self.fitsimage.get_zoom()
        if zoomlevel >= -4:
            return 14
        elif zoomlevel >= -6:
            return 12
        elif zoomlevel >= -8:
            return 10
        else:
            return 8

    def rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        a = x - xoff
        b = y - yoff
        cos_t = math.cos(math.radians(theta))
        sin_t = math.sin(math.radians(theta))
        ap = (a * cos_t) - (b * sin_t)
        bp = (a * sin_t) + (b * cos_t)
        return (ap + xoff, bp + yoff)


class CompoundMixin(object):
    """A CompoundMixin makes an object that is an aggregation of other objects.
    It is used to make generic compound drawing types as well as (for example)
    layers of canvases on top of an image.
    """

    def __init__(self):
        # holds a list of objects to be drawn
        self.objects = []

    def contains(self, x, y):
        for obj in self.objects:
            if obj.contains(x, y):
                return True
        return False

    def getItemsAt(self, x, y):
        res = []
        for obj in self.objects:
            if obj.contains(x, y):
                res.insert(0, obj)
        return res
        
    def initialize(self, tag, fitsimage, logger):
        self.tag = tag
        self.fitsimage = fitsimage
        self.logger = logger

        # TODO: subtags for objects?
        for obj in self.objects:
            obj.initialize(None, fitsimage, logger)

    def isCompound(self):
        return True
    
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
        #obj.initialize(None, self.fitsimage, self.logger)
        obj.fitsimage = self.fitsimage
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
            

class CanvasMixin(object):
    """A CanvasMixin is combined with the CompoundMixin to make a
    tag-addressible canvas-like interface.  This mixin should precede the
    CompoundMixin in the inheritance (and so, method resolution) order.
    """

    def __init__(self):
        assert isinstance(self, CompoundMixin), "Missing CompoundMixin class"
        # holds the list of tags
        self.tags = {}
        self.count = 0

    def add(self, obj, tag=None, tagpfx=None, belowThis=None, redraw=True):
        self.count += 1
        if tag:
            # user supplied a tag
            if self.tags.has_key(tag):
                raise CanvasObjectError("Tag already used: '%s'" % (tag))
        else:
            if tagpfx:
                # user supplied a tag prefix
                if tagpfx.startswith('@'):
                    raise CanvasObjectError("Tag prefix may not begin with '@'")
                tag = '%s%d' % (tagpfx, self.count)
            else:
                # make up our own tag
                tag = '@%d' % (self.count)
                
        obj.initialize(tag, self.fitsimage, self.logger)
        #obj.initialize(tag, self.fitsimage, self.fitsimage.logger)
        self.tags[tag] = obj
        self.addObject(obj, belowThis=belowThis)

        if redraw:
            self.redraw(whence=3)
        return tag
        
    def deleteObjectsByTag(self, tags, redraw=True):
        for tag in tags:
            try:
                obj = self.tags[tag]
                del self.tags[tag]
                super(CanvasMixin, self).deleteObject(obj)
            except Exception, e:
                continue
        
        if redraw:
            self.redraw(whence=3)

    def deleteObjectByTag(self, tag, redraw=True):
        self.deleteObjectsByTag([tag], redraw=redraw)

    def getObjectByTag(self, tag):
        obj = self.tags[tag]
        return obj

    def getTagsByTagpfx(self, tagpfx):
        res = []
        keys = filter(lambda k: k.startswith(tagpfx), self.tags.keys())
        return keys

    def getObjectsByTagpfx(self, tagpfx):
        return map(lambda k: self.tags[k], self.getTagsByTagpfx(tagpfx))

    def deleteAllObjects(self, redraw=True):
        self.tags = {}
        CompoundMixin.deleteAllObjects(self)
        
        if redraw:
            self.redraw(whence=3)

    def deleteObjects(self, objects, redraw=True):
        for tag, obj in self.tags.items():
            if obj in objects:
                self.deleteObjectByTag(tag, redraw=False)
        
        if redraw:
            self.redraw(whence=3)

    def deleteObject(self, obj, redraw=True):
        self.deleteObjects([obj], redraw=redraw)
        
    def raiseObjectByTag(self, tag, aboveThis=None, redraw=True):
        obj1 = self.getObjectByTag(tag)
        if not aboveThis:
            self.raiseObject(obj1)
        else:
            obj2 = self.getObjectByTag(aboveThis)
            self.raiseObject(obj1, obj2)

        if redraw:
            self.redraw(whence=3)

    def lowerObjectByTag(self, tag, belowThis=None, redraw=True):
        obj1 = self.getObjectByTag(tag)
        if not belowThis:
            self.lowerObject(obj1)
        else:
            obj2 = self.getObjectByTag(belowThis)
            self.lowerObject(obj1, obj2)

        if redraw:
            self.redraw(whence=3)
            

class DrawingMixin(object):
    """The DrawingMixin is a mixin class that adds drawing capability for
    some of the basic CanvasObject-derived types.  The setSurface method is
    used to associate a FitsImageCanvas object for layering on.
    """

    def __init__(self, drawDict):
        # For interactive drawing
        self.candraw = False
        self._isdrawing = False
        self.drawDict = drawDict
        self.drawtypes = drawDict.keys()
        self.t_drawtype = 'point'
        self.t_drawparams = {}
        self._start_x = 0
        self._start_y = 0
        self.processTime = 0.0
        # time delta threshold for deciding whether to update the image
        self.deltaTime = 0.020
        self.drawObj = None

        self.fitsobj = None
        self.drawbuttonmask = 0x4

        # NOTE: must be mixed in with a Callback.Callbacks
        for name in ('draw-event',):
            self.enable_callback(name)

        self.set_callback('button-press', self.draw_start)
        self.set_callback('motion', self.draw_motion)
        self.set_callback('button-release', self.draw_stop)

    def setSurface(self, fitsimage):
        self.fitsimage = fitsimage
        #self.ui_setActive(True)

    def getSurface(self):
        return self.fitsimage

    def draw(self):
        super(DrawingMixin, self).draw()
        if self.drawObj:
            self.drawObj.draw()

    def get_ruler_distances(self, x1, y1, x2, y2):
        mode = self.t_drawparams.get('units', 'arcmin')
        try:
            image = self.fitsimage.image
            if mode == 'arcmin':
                # Calculate RA and DEC for the three points
                # origination point
                ra_org, dec_org = image.pixtoradec(x1, y1)

                # destination point
                ra_dst, dec_dst = image.pixtoradec(x2, y2)

                # "heel" point making a right triangle
                ra_heel, dec_heel = image.pixtoradec(x2, y1)

                text_h = image.get_starsep_RaDecDeg(ra_org, dec_org, ra_dst, dec_dst)
                text_x = image.get_starsep_RaDecDeg(ra_org, dec_org, ra_heel, dec_heel)
                text_y = image.get_starsep_RaDecDeg(ra_heel, dec_heel, ra_dst, dec_dst)
            else:
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                dh = math.sqrt(dx**2 + dy**2)
                text_x = str(dx)
                text_y = str(dy)
                text_h = ("%.3f" % dh)
                
        except Exception, e:
            text_h = 'BAD WCS'
            text_x = 'BAD WCS'
            text_y = 'BAD WCS'

        return (text_x, text_y, text_h)

    def _draw_update(self, data_x, data_y):

        klass = self.drawDict[self.t_drawtype]
        obj = None
        
        if self.t_drawtype == 'point':
            radius = max(abs(self._start_x - data_x),
                         abs(self._start_y - data_y))
            obj = klass(self._start_x, self._start_y, radius,
                        **self.t_drawparams)

        elif self.t_drawtype == 'rectangle':
            if not self.fitsimage.isshiftdown:
                obj = klass(self._start_x, self._start_y,
                            data_x, data_y, **self.t_drawparams)
                
            else:
                # if holding the shift key, constrain to a square
                len_x = self._start_x - data_x
                len_y = self._start_y - data_y
                length = max(abs(len_x), abs(len_y))
                len_x = cmp(len_x, 0) * length
                len_y = cmp(len_y, 0) * length
                obj = klass(self._start_x, self._start_y,
                            self._start_x-len_x, self._start_y-len_y,
                            **self.t_drawparams)

        elif self.t_drawtype == 'circle':
            # radius = max(abs(self._start_x - data_x),
            #              abs(self._start_y - data_y))
            radius = math.sqrt(abs(self._start_x - data_x)**2 + 
                               abs(self._start_y - data_y)**2 )
            obj = klass(self._start_x, self._start_y, radius,
                        **self.t_drawparams)

        elif self.t_drawtype == 'line':
            obj = klass(self._start_x, self._start_y, data_x, data_y,
                        **self.t_drawparams)

        elif self.t_drawtype == 'triangle':
            obj = klass(self._start_x, self._start_y, data_x, data_y,
                        **self.t_drawparams)

        elif self.t_drawtype == 'ruler':
            text_x, text_y, text_h = self.get_ruler_distances(self._start_x,
                                                              self._start_y,
                                                              data_x, data_y)
            obj = klass(self._start_x, self._start_y, data_x, data_y,
                        text_x=text_x, text_y=text_y, text_h = text_h,
                        **self.t_drawparams)

        if obj != None:
            obj.initialize(None, self.fitsimage, self.logger)
            #obj.initialize(None, self.fitsimage, self.fitsimage.logger)
            self.drawObj = obj
            if time.time() - self.processTime > self.deltaTime:
                self.processDrawing()
            
        return True
            
    def draw_start(self, canvas, button, data_x, data_y):
        #if self.candraw and ((button == 0x4) or (button == 0x11)):
        if self.candraw and (button & 0x4):
            self._isdrawing = True
            self._start_x = data_x
            self._start_y = data_y
            self._draw_update(data_x, data_y)
            self.processDrawing()

    def draw_stop(self, canvas, button, data_x, data_y):
        if self.candraw and self._isdrawing:
            self._draw_update(data_x, data_y)
            self._isdrawing = False
            obj, self.drawObj = self.drawObj, None

            if obj:
                objtag = self.add(obj, redraw=True)
                return self.make_callback('draw-event', objtag)
            else:
                self.processDrawing()
                
            return True

    def draw_motion(self, canvas, button, data_x, data_y):
        if self._isdrawing:
            self._draw_update(data_x, data_y)

    def processDrawing(self):
        self.processTime = time.time()
        self.fitsimage.redraw(whence=3)
    
    def isDrawing(self):
        return self._isdrawing
    
    def enable_draw(self, tf):
        self.candraw = tf
        
    def set_drawcolor(self, colorname):
        self.t_drawparams['color'] = colorname
        
    def set_drawtype(self, drawtype, **drawparams):
        assert drawtype in self.drawtypes, \
               CanvasObjectError("Bad drawing type '%s': must be one of %s" % (
            drawtype, self.drawtypes))
        self.t_drawtype = drawtype
        self.t_drawparams = drawparams.copy()

    def get_drawtypes(self):
        return self.drawtypes

    def get_drawtype(self):
        return self.t_drawtype

    def get_drawparams(self):
        return self.t_drawparams.copy()


# END
