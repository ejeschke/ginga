#
# Histogram.py -- Histogram plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.misc import Widgets, Plot
from ginga import GingaPlugin

class Histogram(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Histogram, self).__init__(fv, fitsimage)

        self.layertag = 'histogram-canvas'
        self.histtag = None
        self.histcolor = 'aquamarine'
        # If True, limits X axis to lo/hi cut levels
        self.xlimbycuts = True
        # Number of histogram bins
        self.numbins = 2048

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
        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        # Make the cuts plot
        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=0)

        self.plot = Plot.Plot(self.logger, width=2, height=3, dpi=100)
        ax = self.plot.add_axis()
        ax.grid(True)
        
        # for now we need to wrap this native widget
        w = Widgets.wrap(self.plot.get_widget())
        vbox.add_widget(w, stretch=1)

        captions = (('Cut Low:', 'label', 'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High', 'entry', 'Cut Levels', 'button'),
                    ('Auto Levels', 'button'),
                    ('Log Histogram', 'checkbutton', 'Plot By Cuts', 'checkbutton'),
                    ('NumBins:', 'label', 'NumBins', 'entry'),
                    ('Full Image', 'button'),
                    )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.cut_levels.set_tooltip("Set cut levels manually")
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_high.set_tooltip("Set high cut level (press Enter)")
        b.log_histogram.set_tooltip("Use the log of the pixel values for the histogram (empty bins map to 10^-1)")
        b.plot_by_cuts.set_tooltip("Only show the part of the histogram between the cuts")
        b.numbins.set_tooltip("Number of bins for the histogram")
        b.full_image.set_tooltip("Use the full image for calculating the histogram")
        b.numbins.set_text(str(self.numbins))
        b.cut_low.add_callback('activated', lambda w: self.cut_levels())
        b.cut_high.add_callback('activated', lambda w: self.cut_levels())
        b.cut_levels.add_callback('activated', lambda w: self.cut_levels())
        b.auto_levels.add_callback('activated', lambda w: self.auto_levels())

        b.log_histogram.set_state(self.plot.logy)
        b.log_histogram.add_callback('activated', self.log_histogram_cb)
        b.plot_by_cuts.set_state(self.xlimbycuts)
        b.plot_by_cuts.add_callback('activated', self.plot_by_cuts_cb)
        b.numbins.add_callback('activated', lambda w: self.set_numbins_cb())
        b.full_image.add_callback('activated', lambda w: self.full_image_cb())

        vbox.add_widget(w, stretch=0)

        ## spacer = Widgets.Label('')
        ## vbox.add_widget(spacer, stretch=1)
        
        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)
        self.gui_up = True

    def instructions(self):
        self.tw.set_text("""Draw (or redraw) a region with the right mouse button.  Click or drag left mouse button to reposition region.""")

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
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

    def full_image_cb(self):
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

        numbins = self.numbins
        ## pct = 1.0
        ## i = int(numbins * (1.0 - pct))
        ## j = int(numbins * pct)

        depth = image.get_depth()
        if depth != 3:
            res = image.histogram(int(bbox.x1), int(bbox.y1),
                                  int(bbox.x2), int(bbox.y2),
                                  pct=1.0, numbins=numbins)
            # used with 'steps-post' drawstyle, this x and y assignment
                # gives correct histogram-steps
            x = res.bins
            y = numpy.append(res.dist, res.dist[-1])
            ## y, x = y[i:j+1], x[i:j+1]
            ymax = y.max()
            if self.plot.logy:
                y = numpy.choose(y > 0, (.1, y))
            self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                           title="Pixel Value Distribution",
                           color='blue', alpha=1.0, drawstyle='steps-post')
        else:
            colors = ('red', 'green', 'blue')
            ymax = 0
            for z in range(depth):
                res = image.histogram(int(bbox.x1), int(bbox.y1),
                                      int(bbox.x2), int(bbox.y2),
                                      z=z, pct=1.0, numbins=numbins)
                # used with 'steps-post' drawstyle, this x and y assignment
                # gives correct histogram-steps
                x = res.bins
                y = numpy.append(res.dist, res.dist[-1])
                ## y, x = y[i:j+1], x[i:j+1]
                ymax = max(ymax, y.max())
                if self.plot.logy:
                    y = numpy.choose(y > 0, (.1, y))
                self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                               title="Pixel Value Distribution",
                               color=colors[z], alpha=0.33, drawstyle='steps-post')

        # show cut levels
        loval, hival = self.fitsimage.get_cut_levels()
        self.loline = self.plot.ax.axvline(loval, 0.0, 0.99,
                                           linestyle='-', color='red')
        self.hiline = self.plot.ax.axvline(hival, 0.0, 0.99,
                                            linestyle='-', color='green')
        if self.xlimbycuts:
            self.plot.ax.set_xlim(loval, hival)

        # Make x axis labels a little more readable
        ## lbls = self.plot.ax.xaxis.get_ticklabels()
        ## for lbl in lbls:
        ##     lbl.set(rotation=45, horizontalalignment='right')
        
        self.w.cut_low.set_text(str(loval))
        self.w.cut_high.set_text(str(hival))
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
            loval = float(self.w.cut_low.get_text())
            hival = float(self.w.cut_high.get_text())

            reslvls = self.fitsimage.cut_levels(loval, hival)
        except Exception as e:
            self.fv.showStatus("Error cutting levels: %s" % (str(e)))

        if self.xlimbycuts:
            self.redo()

        return reslvls

    def auto_levels(self):
        self.fitsimage.auto_levels()

    def cutset_ext_cb(self, setting, value, fitsimage):
        if not self.gui_up:
            return
        t_ = fitsimage.get_settings()
        loval, hival = t_['cuts']

        try:
            self.loline.remove()
            self.hiline.remove()
        except:
            pass
        self.loline = self.plot.ax.axvline(loval, 0.0, 0.99,
                                           linestyle='-', color='black')
        self.hiline = self.plot.ax.axvline(hival, 0.0, 0.99,
                                            linestyle='-', color='black')
        self.w.cut_low.set_text(str(loval))
        self.w.cut_high.set_text(str(hival))
        #self.plot.fig.canvas.draw()
        self.redo()

    def set_numbins_cb(self):
        self.numbins = int(self.w.numbins.get_text())
        self.redo()
        
    def log_histogram_cb(self, w, val):
        self.plot.logy = val
        if (self.histtag is not None) and self.gui_up:
            # self.histtag == None means no data is loaded yet
            self.redo()

    def plot_by_cuts_cb(self, w, val):
        self.xlimbycuts = val
        if (self.histtag is not None) and self.gui_up:
            # self.histtag == None means no data is loaded yet
            self.redo()

    def __str__(self):
        return 'histogram'

# END
