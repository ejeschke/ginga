#
# CutsBase.py -- Cuts plugin base class for Ginga
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
import numpy

class CutsBase(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(CutsBase, self).__init__(fv, fitsimage)

        self.cutscolor = 'green'
        self.layertag = 'cuts-canvas'
        self.cutstag = None
        self.tags = ['None']
        self.count = 0
        self.colors = ['green', 'red', 'blue', 'cyan', 'pink', 'magenta',
                       'orange', 'violet', 'turquoise', 'yellow']
        #self.cuttypes = ['free', 'horizontal', 'vertical', 'cross']
        self.cuttypes = ['free', 'cross']
        self.cuttype = 'free'

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('cursor-down', self.buttondown_cb)
        canvas.set_callback('cursor-move', self.motion_cb)
        canvas.set_callback('cursor-up', self.buttonup_cb)
        canvas.set_callback('key-press', self.keydown)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas


    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def start(self):
        # start line cuts operation
        self.instructions()
        self.plot.set_titles(rtitle="Cuts")

        # insert canvas, if not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        #self.canvas.deleteAllObjects()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a line with the right mouse button")
        self.redo()

    def stop(self):
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.fv.showStatus("")

    def replaceCutsTag(self, oldtag, newtag, select=False):
        self.addCutsTag(newtag, select=select)
        self.deleteCutsTag(oldtag)

    def _plotpoints(self, line, color):
        # Get points on the line
        points = self.fitsimage.get_pixels_on_line(int(line.x1), int(line.y1),
                                                   int(line.x2), int(line.y2))
        points = numpy.array(points)
        self.plot.cuts(points, xtitle="Line Index", ytitle="Pixel Value",
                       color=color)
        
    def _redo(self, lines, colors):
        for idx in xrange(len(lines)):
            line, color = lines[idx], colors[idx]
            line.color = color
            #text = obj.objects[1]
            #text.color = color
            self._plotpoints(line, color)
        return True
    
    def redo(self):
        self.plot.clear()
        idx = 0
        for cutstag in self.tags:
            if cutstag == 'None':
                continue
            obj = self.canvas.getObjectByTag(cutstag)
            if obj.kind != 'compound':
                continue
            lines = self._getlines(obj)
            n = len(lines)
            colors = self.colors[idx:idx+n]
            self._redo(lines, colors)
            idx = (idx+n) % len(self.colors)

        self.canvas.redraw(whence=3)
        self.fv.showStatus("Click or drag left mouse button to reposition cuts")
        return True

    def _movecut(self, obj, data_x, data_y):
        obj.moveTo(data_x, data_y)

    def _create_cut(self, x, y, count, x1, y1, x2, y2, color='cyan'):
        text = "cuts%d" % (count)
        obj = self.dc.CompoundObject(
            self.dc.Line(x1, y1, x2, y2,
                         color=color,
                         cap='ball'),
            self.dc.Text(x, y, text, color=color))
        obj.set_data(cuts=True)
        return obj

    def _combine_cuts(self, *args):
        return self.dc.CompoundObject(*args)
        
    def _append_lists(self, l):
        if len(l) == 0:
            return []
        elif len(l) == 1:
            return l[0]
        else:
            res = l[0]
            res.extend(self._append_lists(l[1:]))
            return res
        
    def _getlines(self, obj):
        if obj.kind == 'compound':
            return self._append_lists(map(self._getlines, obj.objects))
        elif obj.kind == 'line':
            return [obj]
        else:
            return []
        
    def buttondown_cb(self, canvas, button, data_x, data_y):
        return self.motion_cb(canvas, button, data_x, data_y)
    
    def motion_cb(self, canvas, button, data_x, data_y):

        obj = self.canvas.getObjectByTag(self.cutstag)
        lines = self._getlines(obj)
        for line in lines:
            line.linestyle = 'dash'
        self._movecut(obj, data_x, data_y)

        canvas.redraw(whence=3)
        return True
    
    def buttonup_cb(self, canvas, button, data_x, data_y):

        obj = self.canvas.getObjectByTag(self.cutstag)
        lines = self._getlines(obj)
        for line in lines:
            line.linestyle = 'solid'
        self._movecut(obj, data_x, data_y)
        
        self.redo()
        return True

    def keydown(self, canvas, keyname):
        if keyname == 'n':
            self.select_cut(None)
            return True
        elif keyname == 'h':
            self.cut_at('horizontal')
            return True
        elif keyname == 'v':
            self.cut_at('vertical')
            return True
        elif keyname == 'u':
            self.cut_at('cross')
            return True

    def cut_at(self, cuttype):
        """Perform a cut at the last mouse position in the image.
        $cuttype$ determines the type of cut made.
        """
        data_x, data_y = self.fitsimage.get_last_data_xy()
        image = self.fitsimage.get_image()
        wd, ht = image.get_size()

        coords = []
        if cuttype == 'horizontal':
            coords.append((0, data_y, wd-1, data_y))
        elif cuttype == 'vertical':
            coords.append((data_x, 0, data_x, ht-1))
        elif cuttype == 'cross':
            # calculate largest cross cut that centers plots on the point
            n = min(data_x, wd-data_x, data_y, ht-data_y)
            coords.append((data_x-n, data_y, data_x+n, data_y))
            coords.append((data_x, data_y-n, data_x, data_y+n))

        if self.cutstag:
            # Replacing a cut
            self.logger.debug("replacing cut position")
            cutobj = self.canvas.getObjectByTag(self.cutstag)
            self.canvas.deleteObjectByTag(self.cutstag, redraw=False)
            count = cutobj.get_data('count')
        else:
            self.logger.debug("adding cut position")
            self.count += 1
            count = self.count
            
        tag = "cuts%d" % (count)
        cuts = []
        for (x1, y1, x2, y2) in coords:
            # calculate center of line
            wd = x2 - x1
            dw = wd // 2
            ht = y2 - y1
            dh = ht // 2
            x, y = x1 + dw + 4, y1 + dh + 4

            cut = self._create_cut(x, y, count, x1, y1, x2, y2,
                                   color='cyan')
            cuts.append(cut)

        if len(cuts) == 1:
            cut = cuts[0]
        else:
            cut = self._combine_cuts(*cuts)
            
        cut.set_data(count=count)
        self.canvas.add(cut, tag=tag)
        self.addCutsTag(tag, select=True)

        self.logger.debug("redoing cut plots")
        return self.redo()

    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind not in ('line', 'rectangle'):
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        # calculate center of line
        wd = obj.x2 - obj.x1
        dw = wd // 2
        ht = obj.y2 - obj.y1
        dh = ht // 2
        x, y = obj.x1 + dw + 4, obj.y1 + dh + 4

        if self.cutstag:
            # Replacing a cut
            self.logger.debug("replacing cut position")
            cutobj = canvas.getObjectByTag(self.cutstag)
            canvas.deleteObjectByTag(self.cutstag, redraw=False)
            count = cutobj.get_data('count')
        else:
            self.logger.debug("adding cut position")
            self.count += 1
            count = self.count
            
        tag = "cuts%d" % (count)
        if obj.kind == 'line':
            cut = self._create_cut(x, y, count,
                                   obj.x1, obj.y1, obj.x2, obj.y2,
                                   color='cyan')

        elif obj.kind == 'rectangle':
            if self.cuttype == 'horizontal':
                # add horizontal cut at midpoints of rectangle
                cut = self._create_cut(x, y, count,
                                       obj.x1, obj.y1+dh, obj.x2, obj.y1+dh,
                                       color='cyan')

            elif self.cuttype == 'vertical':
                # add vertical cut at midpoints of rectangle
                cut = self._create_cut(x, y, count,
                                       obj.x1+dw, obj.y1, obj.x1+dw, obj.y2,
                                       color='cyan')

            elif self.cuttype == 'cross':
                x, y = obj.x1 + dw//2, obj.y1 + dh - 4
                cut_h = self._create_cut(x, y, count,
                                         obj.x1, obj.y1+dh, obj.x2, obj.y1+dh,
                                         color='cyan')
                x, y = obj.x1 + dw + 4, obj.y1 + dh//2
                cut_v = self._create_cut(x, y, count,
                                       obj.x1+dw, obj.y1, obj.x1+dw, obj.y2,
                                       color='cyan')
                cut = self._combine_cuts(cut_h, cut_v)

        cut.set_data(count=count)
        canvas.add(cut, tag=tag)
        self.addCutsTag(tag, select=True)

        self.logger.debug("redoing cut plots")
        return self.redo()
    
#END
