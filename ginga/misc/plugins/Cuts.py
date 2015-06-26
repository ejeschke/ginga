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
        self.cuttypes = ['line', 'path', 'freepath']
        self.cuttype = 'line'

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

        # control for selecting cut type
        combobox = Widgets.ComboBox()
        for cuttype in self.cuttypes:
            combobox.append_text(cuttype)
        self.w.cuts_type = combobox
        index = self.cuttypes.index(self.cuttype)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_cutsdrawtype_cb)
        combobox.set_tooltip("Choose the cut type")
        hbox.add_widget(combobox)

        btn = Widgets.Button("Delete")
        btn.add_callback('activated', self.delete_cut_cb)
        btn.set_tooltip("Delete selected cut")
        hbox.add_widget(btn)

        btn = Widgets.Button("Delete All")
        btn.add_callback('activated', self.delete_all_cb)
        btn.set_tooltip("Clear all cuts")
        hbox.add_widget(btn)

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
        self.tw.set_text("""Draw (or redraw) a line with the right mouse button.  Click or drag left button to reposition line.

Press 'h' for a full horizontal cut and 'j' for a full vertical cut.

When drawing a path cut, press 'v' to add a vertex.""")

    def select_cut(self, tag):
        # deselect the current selected cut, if there is one
        if self.cutstag is not None:
            try:
                obj = self.canvas.getObjectByTag(self.cutstag)
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

        #self.redo()

    def cut_select_cb(self, w, index):
        tag = self.tags[index]
        if index == 0:
            tag = None
        self.select_cut(tag)

    def set_cutsdrawtype_cb(self, w, index):
        self.cuttype = self.cuttypes[index]
        if self.cuttype == 'line':
            self.canvas.set_drawtype('line', color='cyan', linestyle='dash')
        elif self.cuttype == 'path':
            self.canvas.set_drawtype('path', color='cyan', linestyle='dash')
        elif self.cuttype == 'freepath':
            self.canvas.set_drawtype('freepath', color='cyan', linestyle='dash')

    def delete_cut_cb(self, w):
        tag = self.cutstag
        if tag is None:
            return
        index = self.tags.index(tag)
        self.canvas.deleteObjectByTag(tag)
        self.w.cuts.delete_alpha(tag)
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
        self.w.cuts.set_index(0)
        self.cutstag = None
        self.redo()

    def deleteCutsTag(self, tag, redraw=False):
        self.canvas.deleteObjectByTag(tag, redraw=redraw)
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

    def add_cuts_tag(self, tag, select=False):
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
        self.fitsimage.deleteObjectByTag(self.layertag)
        self.fv.showStatus("")

    ## def replace_cuts_tag(self, oldtag, newtag, select=False):
    ##     self.add_cuts_tag(newtag, select=select)
    ##     self.deleteCutsTag(oldtag)

    def _plotpoints(self, obj, color):
        image = self.fitsimage.get_image()
        # Get points on the line
        if obj.kind == 'line':
            points = image.get_pixels_on_line(int(obj.x1), int(obj.y1),
                                              int(obj.x2), int(obj.y2))
        elif obj.kind in ('path', 'freepath'):
            points = []
            x1, y1 = obj.points[0]
            for x2, y2 in obj.points[1:]:
                pts = image.get_pixels_on_line(int(x1), int(y1),
                                               int(x2), int(y2))
                # don't repeat last point when adding next segment
                points.extend(pts[:-1])
                x1, y1 = x2, y2

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

    def _create_cut(self, x, y, count, x1, y1, x2, y2, color='cyan'):
        text = "cuts%d" % (count)
        line_obj = self.dc.Line(x1, y1, x2, y2, color=color,
                                showcap=False)
        text_obj = self.dc.Text(4, 4, text, color=color, coord='offset',
                                ref_obj=line_obj)
        obj = self.dc.CompoundObject(line_obj, text_obj)
        obj.set_data(cuts=True)
        return obj

    def _create_cut_obj(self, count, cuts_obj, color='cyan'):
        text = "cuts%d" % (count)
        cuts_obj.showcap = False
        cuts_obj.linestyle = 'solid'
        #cuts_obj.color = color
        text_obj = self.dc.Text(4, 4, text, color=color, coord='offset',
                                ref_obj=cuts_obj)
        obj = self.dc.CompoundObject(cuts_obj, text_obj)
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
        elif obj.kind in ('line', 'path', 'freepath'):
            return [obj]
        else:
            return []

    def buttondown_cb(self, canvas, event, data_x, data_y):
        return self.motion_cb(canvas, event, data_x, data_y)

    def motion_cb(self, canvas, event, data_x, data_y):
        obj = self.canvas.getObjectByTag(self.cutstag)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)
        canvas.redraw(whence=3)
        return True

    def buttonup_cb(self, canvas, event, data_x, data_y):
        obj = self.canvas.getObjectByTag(self.cutstag)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)

        self.redo()
        return True

    def keydown(self, canvas, keyname):
        if keyname == 'n':
            self.select_cut(None)
            return True
        elif keyname == 'h':
            self.cut_at('horizontal')
            return True
        elif keyname == 'j':
            self.cut_at('vertical')
            return True

    def _get_cut_index(self):
        if self.cutstag is not None:
            # Replacing a cut
            self.logger.debug("replacing cut position")
            try:
                cutobj = self.canvas.getObjectByTag(self.cutstag)
                self.canvas.deleteObjectByTag(self.cutstag, redraw=False)
                count = cutobj.get_data('count')
            except KeyError:
                self.count += 1
                count = self.count
        else:
            self.logger.debug("adding cut position")
            self.count += 1
            count = self.count
        return count

    def cut_at(self, cuttype):
        """Perform a cut at the last mouse position in the image.
        `cuttype` determines the type of cut made.
        """
        data_x, data_y = self.fitsimage.get_last_data_xy()
        image = self.fitsimage.get_image()
        wd, ht = image.get_size()

        coords = []
        if cuttype == 'horizontal':
            coords.append((0, data_y, wd-1, data_y))
        elif cuttype == 'vertical':
            coords.append((data_x, 0, data_x, ht-1))

        count = self._get_cut_index()
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

        self.canvas.deleteObjectByTag(tag, redraw=False)
        self.canvas.add(cut, tag=tag)
        self.add_cuts_tag(tag, select=True)

        self.logger.debug("redoing cut plots")
        return self.redo()

    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        canvas.deleteObjectByTag(tag, redraw=False)

        if not obj.kind in ('line', 'path', 'freepath'):
            return True

        count = self._get_cut_index()
        tag = "cuts%d" % (count)

        cut = self._create_cut_obj(count, obj, color='cyan')
        cut.set_data(count=count)

        canvas.deleteObjectByTag(tag, redraw=False)
        self.canvas.add(cut, tag=tag)
        self.add_cuts_tag(tag, select=True)

        self.logger.debug("redoing cut plots")
        return self.redo()

    def edit_cb(self, canvas, obj):
        self.redo()
        return True

    def __str__(self):
        return 'cuts'

#END
