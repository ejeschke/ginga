#
# HistogramBase.py -- Histogram base class plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
from ginga import GingaPlugin

class HistogramBase(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(HistogramBase, self).__init__(fv, fitsimage)

        self.layertag = 'histogram-canvas'
        self.histtag = None
        self.histcolor = 'aquamarine'

        self.dc = self.fv.getDrawClasses()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('cursor-down', self.drag)
        canvas.set_callback('cursor-move', self.drag)
        canvas.set_callback('cursor-up', self.update)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.getSetting(name).add_callback('set',
                               self.cutset_ext_cb, fitsimage)


    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def start(self):
        self.instructions()
        self.plot.set_titles(rtitle="Histogram")
        self.plot.show()

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
        self.fv.showStatus("Draw a rectangle with the right mouse button")
        
    def stop(self):
        # remove the rect from the canvas
        ## try:
        ##     self.canvas.deleteObjectByTag(self.histtag, redraw=False)
        ## except:
        ##     pass
        ##self.histtag = None
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.gui_up = False
        self.fv.showStatus("")

    def full_image(self):
        canvas = self.canvas
        try:
            canvas.deleteObjectByTag(self.histtag, redraw=False)
        except:
            pass

        image = self.fitsimage.get_image()
        width, height = image.get_size()
        x1, y1, x2, y2 = 0, 0, width-1, height-1
        tag = canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                           color='cyan',
                                           linestyle='dash'))
        self.draw_cb(canvas, tag)
        
    def redo(self):
        obj = self.canvas.getObjectByTag(self.histtag)
        if obj.kind != 'compound':
            return True
        bbox = obj.objects[0]
        
        # Do histogram on the points within the rect
        image = self.fitsimage.get_image()
        self.plot.clear()

        numbins = 2048
        ## pct = 1.0
        ## i = int(numbins * (1.0 - pct))
        ## j = int(numbins * pct)

        depth = image.get_depth()
        if depth != 3:
            res = image.histogram(int(bbox.x1), int(bbox.y1),
                                  int(bbox.x2), int(bbox.y2),
                                  pct=1.0, numbins=numbins)
            y, x = res.dist, res.bins
            x = x[:-1]
            ## y, x = y[i:j+1], x[i:j+1]
            ymax = y.max()
            self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                           title="Pixel Value Distribution",
                           color='blue', alpha=1.0)
        else:
            colors = ('red', 'green', 'blue')
            ymax = 0
            for z in xrange(depth):
                res = image.histogram(int(bbox.x1), int(bbox.y1),
                                      int(bbox.x2), int(bbox.y2),
                                      z=z, pct=1.0, numbins=numbins)
                y, x = res.dist, res.bins
                x = x[:-1]
                ## y, x = y[i:j+1], x[i:j+1]
                ymax = max(ymax, y.max())
                self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                               title="Pixel Value Distribution",
                               color=colors[z], alpha=0.33)

        # show cut levels
        loval, hival = self.fitsimage.get_cut_levels()
        self.loline = self.plot.ax.axvline(loval, 0.0, 0.99,
                                           linestyle='-', color='black')
        self.hiline = self.plot.ax.axvline(hival, 0.0, 0.99,
                                            linestyle='-', color='black')
        self._setText(self.w.cut_low, str(loval))
        self._setText(self.w.cut_high, str(hival))
        self.plot.fig.canvas.draw()

        self.fv.showStatus("Click or drag left mouse button to move region")
        return True
    
    def update(self, canvas, button, data_x, data_y):
        
        obj = self.canvas.getObjectByTag(self.histtag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1+dx, bbox.y1+dy, bbox.x2+dx, bbox.y2+dy
        
        try:
            canvas.deleteObjectByTag(self.histtag, redraw=False)
        except:
            pass

        tag = canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                           color='cyan',
                                           linestyle='dash'))

        self.draw_cb(canvas, tag)
        return True

    def drag(self, canvas, button, data_x, data_y):
        
        obj = self.canvas.getObjectByTag(self.histtag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1+dx, bbox.y1+dy, bbox.x2+dx, bbox.y2+dy

        if obj.kind == 'compound':
            try:
                canvas.deleteObjectByTag(self.histtag, redraw=False)
            except:
                pass

            self.histtag = canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                        color='cyan',
                                                        linestyle='dash'))
        else:
            bbox.x1, bbox.y1, bbox.x2, bbox.y2 = x1, y1, x2, y2
            canvas.redraw(whence=3)

        return True

    
    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind != 'rectangle':
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        if self.histtag:
            try:
                canvas.deleteObjectByTag(self.histtag, redraw=False)
            except:
                pass

        tag = canvas.add(self.dc.CompoundObject(
            self.dc.Rectangle(obj.x1, obj.y1, obj.x2, obj.y2,
                              color=self.histcolor),
            self.dc.Text(obj.x1, obj.y2+4, "Histogram",
                         color=self.histcolor)))
        self.histtag = tag

        return self.redo()
    
    def cut_levels(self):
        try:
            loval = float(self._getText(self.w.cut_low))
            hival = float(self._getText(self.w.cut_high))

            return self.fitsimage.cut_levels(loval, hival)
        except Exception, e:
            self.fv.showStatus("Error cutting levels: %s" % (str(e)))
            
        return True

    def auto_levels(self):
        self.fitsimage.auto_levels()

    def cutset_ext_cb(self, setting, value, fitsimage):
        if not self.gui_up:
            return
        t_ = fitsimage.get_settings()
        loval, hival = t_['cuts']
        
        self.loline.remove()
        self.hiline.remove()
        self.loline = self.plot.ax.axvline(loval, 0.0, 0.99,
                                           linestyle='-', color='black')
        self.hiline = self.plot.ax.axvline(hival, 0.0, 0.99,
                                            linestyle='-', color='black')
        self._setText(self.w.cut_low, str(loval))
        self._setText(self.w.cut_high, str(hival))
        self.plot.fig.canvas.draw()
        
# END
