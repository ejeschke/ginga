#
# Cuts.py -- Cuts plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.misc import Widgets, Plot
from ginga import GingaPlugin
from ginga.util.six.moves import map, zip

class Cuts(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

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
        canvas.enable_edit(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_callback('cursor-down', self.buttondown_cb)
        canvas.set_callback('cursor-move', self.motion_cb)
        canvas.set_callback('cursor-up', self.buttonup_cb)
        canvas.set_callback('key-press', self.keydown)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        # Make the cuts plot
        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_margins(4, 4, 4, 4)
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

        self.plot = Plot.Cuts(self.logger, width=2, height=3, dpi=100)
        ax = self.plot.add_axis()
        ax.grid(True)

        # for now we need to wrap this native widget
        w = Widgets.wrap(self.plot.get_widget())
        vbox.add_widget(w, stretch=1)

        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        hbox.set_border_width(4)

        # control for selecting a cut
        combobox = Widgets.ComboBox()
        for tag in self.tags:
            combobox.append_text(tag)
        if self.cutstag is None:
            combobox.set_index(0)
        else:
            combobox.show_text(self.cutstag)
        combobox.add_callback('activated', self.cut_select_cb)
        self.w.cuts = combobox
        combobox.set_tooltip("Select a cut")
        hbox.add_widget(combobox)

        btn = Widgets.Button("Delete")
        btn.add_callback('activated', self.delete_cut_cb)
        btn.set_tooltip("Delete selected cut")
        hbox.add_widget(btn)
        
        btn = Widgets.Button("Delete All")
        btn.add_callback('activated', self.delete_all_cb)
        btn.set_tooltip("Clear all cuts")
        hbox.add_widget(btn)
        
        combobox = Widgets.ComboBox()
        for cuttype in self.cuttypes:
            combobox.append_text(cuttype)
        self.w.cuts_type = combobox
        index = self.cuttypes.index(self.cuttype)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_cutsdrawtype_cb)
        combobox.set_tooltip("Choose the cut type")
        hbox.add_widget(combobox)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(hbox, stretch=0)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(vbox2, stretch=0)
 
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
        self.tw.set_text("""Draw (or redraw) a line with the right mouse button.  Click or drag left button to reposition line.""")
            
    def select_cut(self, tag):
        # deselect the current selected cut, if there is one
        if self.cutstag is not None:
            try:
                obj = self.canvas.getObjectByTag(self.cutstag)
                #obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass
            
        self.cutstag = tag
        if tag is None:
            self.w.cuts.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.cuts.show_text(tag)
        obj = self.canvas.getObjectByTag(tag)
        #obj.setAttrAll(color=self.select_color)

        #self.redo()
        
    def cut_select_cb(self, w, index):
        tag = self.tags[index]
        if index == 0:
            tag = None
        self.select_cut(tag)

    def pan2mark_cb(self, w):
        self.pan2mark = w.get_state()
        
    def set_cutsdrawtype_cb(self, w, index):
        self.cuttype = self.cuttypes[index]
        if self.cuttype in ('free', ):
            self.canvas.set_drawtype('line', color='cyan', linestyle='dash')
        else:
            self.canvas.set_drawtype('square', color='cyan',
                                     linestyle='dash')

    def delete_cut_cb(self, w):
        tag = self.cutstag
        if tag is None:
            return
        index = self.tags.index(tag)
        self.canvas.deleteObjectByTag(tag)
        self.w.cuts.removeItem(index)
        self.tags.remove(tag)
        idx = len(self.tags) - 1
        tag = self.tags[idx]
        if tag == 'None':
            tag = None
        self.select_cut(tag)
        if tag is not None:
            self.redo()
        
    def delete_all_cb(self, w):
        self.canvas.deleteAllObjects()
        self.w.cuts.clear()
        self.tags = ['None']
        self.w.cuts.append_text('None')
        self.w.cuts.setCurrentIndex(0)
        self.cutstag = None
        self.redo()
        
    def deleteCutsTag(self, tag, redraw=False):
        try:
            self.canvas.deleteObjectByTag(tag, redraw=redraw)
        except:
            pass
        try:
            self.tags.remove(tag)
        except:
            pass
        if tag == self.cutstag:
            #self.unhighlightTag(tag)
            if len(self.tags) == 0:
                self.cutstag = None
            else:
                self.cutstag = self.tags[0]
                #self.highlightTag(self.cutstag)
        
    def addCutsTag(self, tag, select=False):
        if not tag in self.tags:
            self.tags.append(tag)
            self.w.cuts.append_text(tag)

        if select:
            if self.cutstag is not None:
                #self.unhighlightTag(self.cutstag)
                pass
            self.cutstag = tag
            self.w.cuts.show_text(tag)
            #self.highlightTag(self.cutstag)
        
    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        self.gui_up = False
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
        # turn off any mode user may be in
        self.modes_off()

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
        image = self.fitsimage.get_image()
        # Get points on the line
        points = image.get_pixels_on_line(int(line.x1), int(line.y1),
                                          int(line.x2), int(line.y2))
        points = numpy.array(points)
        self.plot.cuts(points, xtitle="Line Index", ytitle="Pixel Value",
                       color=color)
        
    def _redo(self, lines, colors):
        for idx in range(len(lines)):
            line, color = lines[idx], colors[idx]
            line.color = color
            #text = obj.objects[1]
            #text.color = color
            self._plotpoints(line, color)

        # Make x axis labels a little more readable
        ## lbls = self.plot.ax.xaxis.get_ticklabels()
        ## for lbl in lbls:
        ##     lbl.set(rotation=45, horizontalalignment='right')
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
        obj.move_to(data_x, data_y)

    def _create_cut(self, x, y, count, x1, y1, x2, y2, color='cyan'):
        text = "cuts%d" % (count)
        line_obj = self.dc.Line(x1, y1, x2, y2, color=color,
                                showcap=True)
        text_obj = self.dc.Text(4, 4, text, color=color, coord='offset',
                                ref_obj=line_obj)
        obj = self.dc.CompoundObject(line_obj, text_obj)
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
            return self._append_lists(list(map(self._getlines, obj.objects)))
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
        if obj.kind == 'line':
            x1, y1 = obj.crdmap.to_data(obj.x1, obj.y1)
            x2, y2 = obj.crdmap.to_data(obj.x2, obj.y2)
        elif obj.kind == 'rectangle':
            x1, y1, x2, y2 = obj.get_llur()
        else:
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        # calculate center of line
        wd = x2 - x1
        dw = wd // 2
        ht = y2 - y1
        dh = ht // 2
        x, y = x1 + dw + 4, y1 + dh + 4

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
                                   x1, y1, x2, y2, color='cyan')

        elif obj.kind == 'rectangle':
            if self.cuttype == 'horizontal':
                # add horizontal cut at midpoints of rectangle
                cut = self._create_cut(x, y, count,
                                       x1, y1+dh, x2, y1+dh,
                                       color='cyan')

            elif self.cuttype == 'vertical':
                # add vertical cut at midpoints of rectangle
                cut = self._create_cut(x, y, count,
                                       x1+dw, y1, x1+dw, y2,
                                       color='cyan')

            elif self.cuttype == 'cross':
                x, y = x1 + dw//2, y1 + dh - 4
                cut_h = self._create_cut(x, y, count,
                                         x1, y1+dh, x2, y1+dh,
                                         color='cyan')
                x, y = x1 + dw + 4, y1 + dh//2
                cut_v = self._create_cut(x, y, count,
                                       x1+dw, y1, x1+dw, y2,
                                       color='cyan')
                cut = self._combine_cuts(cut_h, cut_v)

        cut.set_data(count=count)
        canvas.add(cut, tag=tag)
        self.addCutsTag(tag, select=True)

        self.logger.debug("redoing cut plots")
        return self.redo()
    
    def edit_cb(self, canvas, obj):
        self.redo()
        return True
    
    def __str__(self):
        return 'cuts'
    
#END
