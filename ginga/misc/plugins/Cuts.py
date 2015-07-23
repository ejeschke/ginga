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
from ginga import GingaPlugin, colors
from ginga.util.six.moves import map, zip

# default cut colors
cut_colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink',
              'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']


class Cuts(GingaPlugin.LocalPlugin):
    """
    A plugin for generating a plot of the values along a line or path.

    There are three kinds of cuts available: line, path and freepath.
    The 'line' cut is a straight line between two points.  The 'path' cut
    is drawn like an open polygon, with straight segments in-between.
    The 'freepath' cut is like a path cut, but drawn using a free-form
    stroke following the cursor movement.  The 'beziercurve' path is a
    cubic Bezier curve.

    Multiple cuts can be plotted.

    Drawing Cuts
    ------------
    The New Cut Type menu chooses what kind of cut you are going to draw.

    Choose "New Cut" from the Cut dropdown menu if you want to draw a
    new cut. Otherwise, if a particular named cut is selected then that
    will be replaced by any newly drawn cut.

    While drawing a path or beziercurve cut, press 'v' to add a vertex,
    or 'z' to remove the last vertex added.

    Keyboard Shortcuts
    ------------------
    While hovering the cursor, press 'h' for a full horizontal cut and
    'j' for a full vertical cut.

    Deleting Cuts
    -------------
    To delete a cut select its name from the Cut dropdown and click the
    Delete button.  To delete all cuts press "Delete All".

    Editing Cuts
    ------------
    Using the edit canvas function it is possible to add new vertexes to
    an existing path, and to move vertexes around.   Press 'b' to enter
    edit mode and then press 'l' to lock it (you can also click the lock
    icon).  Now you can select the line or path by clicking on it, which
    should enable the control points at the ends or vertexes--you can drag
    these around.  To add a new vertex to a path, hover the cursor carefully
    on the line where you want the new vertex and press 'v'.  To get rid of
    a vertex, hover the cursor over it and press 'z'.  You will notice one
    extra control point for the path, which seems to be out to the
    side--this is a movement control point for moving the entire path
    around the image when in edit mode.

    To get out of edit mode, press Escape or 'l' again (or click the lock
    icon again).
    """

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

        self.layertag = 'cuts-canvas'
        self._new_cut = 'New Cut'
        self.cutstag = self._new_cut
        self.tags = [self._new_cut]
        self.count = 0
        self.cuttypes = ['line', 'path', 'freepath', 'beziercurve']
        self.cuttype = 'line'

        # get Cuts preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Cuts')
        self.settings.addDefaults(select_new_cut=True, label_cuts=True,
                                  colors=cut_colors)
        self.settings.load(onError='silent')
        self.colors = self.settings.get('colors', cut_colors)

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.add_draw_mode('move', down=self.buttondown_cb,
                             move=self.motion_cb, up=self.buttonup_cb,
                             key=self.keydown)
        canvas.set_draw_mode('draw')
        canvas.register_for_cursor_drawing(self.fitsimage)
        #canvas.set_callback('key-press', self.keydown)
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

        captions = (('Cut:', 'label', 'Cut', 'combobox',
                     'New Cut Type:', 'label', 'Cut Type', 'combobox'),
                    ('Delete Cut', 'button', 'Delete All', 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # control for selecting a cut
        combobox = b.cut
        for tag in self.tags:
            combobox.append_text(tag)
        combobox.show_text(self.cutstag)
        combobox.add_callback('activated', self.cut_select_cb)
        self.w.cuts = combobox
        combobox.set_tooltip("Select a cut to redraw or delete")

        # control for selecting cut type
        combobox = b.cut_type
        for cuttype in self.cuttypes:
            combobox.append_text(cuttype)
        self.w.cuts_type = combobox
        index = self.cuttypes.index(self.cuttype)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_cutsdrawtype_cb)
        combobox.set_tooltip("Choose the cut type to draw")

        btn = b.delete_cut
        btn.add_callback('activated', self.delete_cut_cb)
        btn.set_tooltip("Delete selected cut")

        btn = b.delete_all
        btn.add_callback('activated', self.delete_all_cb)
        btn.set_tooltip("Clear all cuts")

        vbox2 = Widgets.VBox()
        vbox2.add_widget(w, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback('activated', lambda w, val: self.set_mode_cb('move'))
        btn1.set_tooltip("Choose this to position cuts")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated', lambda w, val: self.set_mode_cb('draw'))
        btn2.set_tooltip("Choose this to draw a new or replacement cut")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated', lambda w, val: self.set_mode_cb('edit'))
        btn3.set_tooltip("Choose this to edit a cut")
        self.w.btn_edit = btn3
        hbox.add_widget(btn3)

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

        self.select_cut(self._new_cut)
        self.gui_up = True

    def instructions(self):
        self.tw.set_text("""When drawing a path or Bezier cut, press 'v' to add a vertex.

Keyboard shortcuts: press 'h' for a full horizontal cut and 'j' for a full vertical cut.""")

    def select_cut(self, tag):
        self.cutstag = tag
        self.w.cuts.show_text(tag)

        if (tag == self._new_cut) or len(self.tags) < 2:
            self.w.delete_cut.set_enabled(False)
            self.w.delete_all.set_enabled(False)

            self.w.btn_move.set_enabled(False)
            self.w.btn_draw.set_state(True)
            self.w.btn_edit.set_enabled(False)
        else:
            self.w.delete_cut.set_enabled(True)
            self.w.delete_all.set_enabled(True)

            self.w.btn_move.set_enabled(True)
            self.w.btn_edit.set_enabled(True)

            if self.w.btn_edit.get_state():
                self.edit_select_cuts()

    def cut_select_cb(self, w, index):
        tag = self.tags[index]
        self.select_cut(tag)

    def set_cutsdrawtype_cb(self, w, index):
        self.cuttype = self.cuttypes[index]
        self.canvas.set_drawtype(self.cuttype, color='cyan',
                                 linestyle='dash')

    def delete_cut_cb(self, w):
        tag = self.cutstag
        if tag == self._new_cut:
            return
        index = self.tags.index(tag)
        self.canvas.deleteObjectByTag(tag)
        self.w.cuts.delete_alpha(tag)
        self.tags.remove(tag)
        idx = len(self.tags) - 1
        tag = self.tags[idx]
        self.select_cut(tag)
        # plot cleared in redo() if no more cuts
        self.redo()

    def delete_all_cb(self, w):
        self.canvas.deleteAllObjects()
        self.w.cuts.clear()
        self.tags = [self._new_cut]
        self.cutstag = self._new_cut
        self.w.cuts.append_text(self._new_cut)
        self.select_cut(self._new_cut)
        # plot cleared in redo() if no more cuts
        self.redo()

    def add_cuts_tag(self, tag, select=False):
        if not tag in self.tags:
            self.tags.append(tag)
            self.w.cuts.append_text(tag)

        self.w.delete_cut.set_enabled(True)
        self.w.delete_all.set_enabled(True)

        if select:
            self.select_cut(tag)

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
        self.canvas.set_draw_mode('move')
        self.fv.showStatus("")

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
        elif obj.kind == 'beziercurve':
            points = obj.get_pixels_on_curve(image)
        points = numpy.array(points)

        rgb = colors.lookup_color(color)
        self.plot.cuts(points, xtitle="Line Index", ytitle="Pixel Value",
                       color=rgb)

    def _redo(self, lines, colors):
        for idx in range(len(lines)):
            line, color = lines[idx], colors[idx]
            line.color = color
            self._plotpoints(line, color)

        return True

    def redo(self):
        self.plot.clear()
        idx = 0
        for cutstag in self.tags:
            if cutstag == self._new_cut:
                continue
            obj = self.canvas.getObjectByTag(cutstag)
            if obj.kind != 'compound':
                continue
            lines = self._getlines(obj)
            n = len(lines)
            count = obj.get_data('count', self.count)
            idx = (count + n) % len(self.colors)
            colors = self.colors[idx:idx+n]
            # text should take same color as first line in line set
            text = obj.objects[1]
            if text.kind == 'text':
                text.color = colors[0]
            #text.color = color
            self._redo(lines, colors)

        # force mpl redraw
        self.plot.fig.canvas.draw()

        self.canvas.redraw(whence=3)
        self.fv.showStatus("Click or drag left mouse button to reposition cuts")
        return True

    def _create_cut(self, x, y, count, x1, y1, x2, y2, color='cyan'):
        text = "cuts%d" % (count)
        if not self.settings.get('label_cuts', False):
            text = ''
        line_obj = self.dc.Line(x1, y1, x2, y2, color=color,
                                showcap=False)
        text_obj = self.dc.Text(4, 4, text, color=color, coord='offset',
                                ref_obj=line_obj)
        obj = self.dc.CompoundObject(line_obj, text_obj)
        obj.set_data(cuts=True)
        return obj

    def _create_cut_obj(self, count, cuts_obj, color='cyan'):
        text = "cuts%d" % (count)
        if not self.settings.get('label_cuts', False):
            text = ''
        cuts_obj.showcap = False
        cuts_obj.linestyle = 'solid'
        #cuts_obj.color = color
        color = cuts_obj.color
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
        elif obj.kind in self.cuttypes:
            return [obj]
        else:
            return []

    def buttondown_cb(self, canvas, event, data_x, data_y, viewer):
        return self.motion_cb(canvas, event, data_x, data_y, viewer)

    def motion_cb(self, canvas, event, data_x, data_y, viewer):
        if self.cutstag == self._new_cut:
            return True
        obj = self.canvas.getObjectByTag(self.cutstag)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)
        canvas.redraw(whence=3)
        return True

    def buttonup_cb(self, canvas, event, data_x, data_y, viewer):
        if self.cutstag == self._new_cut:
            return True
        obj = self.canvas.getObjectByTag(self.cutstag)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)

        self.redo()
        return True

    def keydown(self, canvas, event, data_x, data_y, viewer):
        if event.key == 'n':
            self.select_cut(self._new_cut)
            return True
        elif event.key == 'h':
            self.cut_at('horizontal')
            return True
        elif event.key == 'j':
            self.cut_at('vertical')
            return True
        return False

    def _get_new_count(self):
        counts = set([])
        for cutstag in self.tags:
            try:
                obj = self.canvas.getObjectByTag(cutstag)
            except KeyError:
                continue
            counts.add(obj.get_data('count', 0))
        ncounts = set(range(len(self.colors)))
        avail = list(ncounts.difference(counts))
        avail.sort()
        if len(avail) > 0:
            count = avail[0]
        else:
            self.count += 1
            count = self.count
        return count

    def _get_cut_index(self):
        if self.cutstag != self._new_cut:
            # Replacing a cut
            self.logger.debug("replacing cut position")
            try:
                cutobj = self.canvas.getObjectByTag(self.cutstag)
                self.canvas.deleteObjectByTag(self.cutstag, redraw=False)
                count = cutobj.get_data('count')
            except KeyError:
                count = self._get_new_count()
        else:
            self.logger.debug("adding cut position")
            count = self._get_new_count()
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
        select_flag = self.settings.get('select_new_cut', True)
        self.add_cuts_tag(tag, select=select_flag)

        self.logger.debug("redoing cut plots")
        return self.redo()

    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        canvas.deleteObjectByTag(tag, redraw=False)

        if not obj.kind in self.cuttypes:
            return True

        count = self._get_cut_index()
        tag = "cuts%d" % (count)

        cut = self._create_cut_obj(count, obj, color='cyan')
        cut.set_data(count=count)

        canvas.deleteObjectByTag(tag, redraw=False)
        self.canvas.add(cut, tag=tag)
        select_flag = self.settings.get('select_new_cut', True)
        self.add_cuts_tag(tag, select=select_flag)

        self.logger.debug("redoing cut plots")
        return self.redo()

    def edit_cb(self, canvas, obj):
        self.redo()
        return True

    def edit_select_cuts(self):
        if self.cutstag != self._new_cut:
            obj = self.canvas.getObjectByTag(self.cutstag)
            # drill down to reference shape
            if hasattr(obj, 'objects'):
                obj = obj.objects[0]
            self.canvas.edit_select(obj)
        else:
            self.canvas.clear_selected()
        self.canvas.update_canvas()

    def set_mode_cb(self, mode):
        self.canvas.set_draw_mode(mode)
        if mode == 'edit':
            self.edit_select_cuts()
        return True

    def __str__(self):
        return 'cuts'

#END
