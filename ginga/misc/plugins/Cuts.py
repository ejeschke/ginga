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

from ginga.gw import Widgets, Plots
from ginga import GingaPlugin, colors
from ginga.util.six.moves import map, zip
from ginga.canvas.coordmap import OffsetMapper

# default cut colors
cut_colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink',
              'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']


class Cuts(GingaPlugin.LocalPlugin):
    """
    A plugin for generating a plot of the values along a line or path.

    There are four kinds of cuts available: line, path, freepath and
    beziercurve.
    - The 'line' cut is a straight line between two points.
    - The 'path' cut is drawn like an open polygon, with straight segments
      in-between.
    - The 'freepath' cut is like a path cut, but drawn using a free-form
      stroke following the cursor movement.
    - The 'beziercurve' path is a cubic Bezier curve.

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
    an existing path, and to move vertexes around.   Click the "Edit"
    radio button to put the canvas in edit mode.  If a cut is not
    automatically selected you can now select the line, path or curve by
    clicking on it, which should enable the control points at the ends or
    vertices--you can drag these around.  To add a new vertex to a path,
    hover the cursor carefully on the line where you want the new vertex
    and press 'v'.  To get rid of a vertex, hover the cursor over it and
    press 'z'.

    You will notice one extra control point for most objects, which has
    a center of a different color--this is a movement control point for
    moving the entire object around the image when in edit mode.

    Changing Width of Cuts
    ----------------------
    The width of 'line' cuts can be changed using the "Width Type" menu:
    - "none" indicates a cut of zero radius; i.e. only showing the pixel
      values along the line
    - "x" will plot the sum of values along the X axis orthoginal to the
      cut.
    - "y" will plot the sum of values along the Y axis orthoginal to the
      cut.
    - "perpendicular" will plot the sum of values along an axis perpendicular
      to the cut.

    The "Width radius" controls the width of the orthoginal summation by
    an amount on either side of the cut--1 would be 3 pixels, 2 would be 5
    pixels, etc.
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
        self.save_enabled = False

        # For collecting data orthogonal to the cut
        self.widthtypes = ['none', 'x', 'y', 'perpendicular']
        self.widthtype = 'none'
        self.width_radius = 5
        self.tine_spacing_px = 100

        # get Cuts preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Cuts')
        self.settings.addDefaults(select_new_cut=True, draw_then_move=True,
                                  label_cuts=True, colors=cut_colors,
                                  show_cuts_legend=False)
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

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        self.plot = Plots.Cuts(self.logger, width=2, height=3, dpi=100)
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

        exp = Widgets.Expander("Cut Width")

        captions = (('Width Type:', 'label', 'Width Type', 'combobox',
                     'Width radius:', 'label', 'Width radius', 'spinbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # control for selecting width cut type
        combobox = b.width_type
        for atype in self.widthtypes:
            combobox.append_text(atype)
        index = self.widthtypes.index(self.widthtype)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_width_type_cb)
        combobox.set_tooltip("Direction of summation orthogonal to cut")

        sb = b.width_radius
        sb.add_callback('value-changed', self.width_radius_changed_cb)
        sb.set_tooltip("Radius of cut width")
        sb.set_limits(1, 100)
        sb.set_value(self.width_radius)

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)
        vbox2.add_widget(exp, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback('activated', lambda w, val: self.set_mode_cb('move', val))
        btn1.set_tooltip("Choose this to position cuts")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated', lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to draw a new or replacement cut")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated', lambda w, val: self.set_mode_cb('edit', val))
        btn3.set_tooltip("Choose this to edit a cut")
        self.w.btn_edit = btn3
        hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
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

        self.save_btn = Widgets.Button("Save")
        self.save_btn.add_callback('activated', lambda w: self.save_cb())
        self.save_btn.set_enabled(self.save_enabled)
        btns.add_widget(self.save_btn, stretch=0)

        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.select_cut(self.cutstag)
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
            self.w.btn_edit.set_enabled(False)
            self.set_mode('draw')
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
        if tag == self._new_cut:
            self.save_btn.set_enabled(False)
        # plot cleared in replot_all() if no more cuts
        self.replot_all()

    def delete_all_cb(self, w):
        self.canvas.deleteAllObjects()
        self.w.cuts.clear()
        self.tags = [self._new_cut]
        self.cutstag = self._new_cut
        self.w.cuts.append_text(self._new_cut)
        self.select_cut(self._new_cut)
        self.save_btn.set_enabled(False)
        # plot cleared in replot_all() if no more cuts
        self.replot_all()

    def add_cuts_tag(self, tag):
        if not tag in self.tags:
            self.tags.append(tag)
            self.w.cuts.append_text(tag)

        self.w.delete_cut.set_enabled(True)
        self.w.delete_all.set_enabled(True)

        select_flag = self.settings.get('select_new_cut', True)
        if select_flag:
            self.select_cut(tag)
            move_flag = self.settings.get('draw_then_move', True)
            if move_flag:
                self.set_mode('move')

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        #self.set_mode('move')
        self.fv.stop_local_plugin(chname, str(self))
        self.gui_up = False
        return True

    def start(self):
        # start line cuts operation
        self.instructions()
        self.plot.set_titles(rtitle="Cuts")

        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        #self.canvas.deleteAllObjects()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a line with the right mouse button")
        self.replot_all()

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        p_canvas.deleteObjectByTag(self.layertag)
        self.fv.showStatus("")

    def redo(self):
        """This is called when a new image arrives or the data in the
        existing image changes.
        """
        self.replot_all()

    def _get_perpendicular_points(self, obj, x, y, r):
        dx = float(obj.x1 - obj.x2)
        dy = float(obj.y1 - obj.y2)
        dist = numpy.sqrt(dx*dx + dy*dy)
        dx /= dist
        dy /= dist
        x3 = x + r * dy
        y3 = y - r * dx
        x4 = x - r * dy
        y4 = y + r * dx
        return (x3, y3, x4, y4)

    def _get_width_points(self, obj, x, y, rx, ry):
        x3, y3 = x - rx, y - ry
        x4, y4 = x + rx, y + ry
        return (x3, y3, x4, y4)

    def get_orthogonal_points(self, obj, x, y, r):
        if self.widthtype == 'x':
            return self._get_width_points(obj, x, y, r, 0)
        elif self.widthtype == 'y':
            return self._get_width_points(obj, x, y, 0, r)
        else:
            return self._get_perpendicular_points(obj, x, y, r)

    def get_orthogonal_array(self, image, obj, x, y, r):
        x1, y1, x2, y2 = self.get_orthogonal_points(obj, x, y, r)
        values = image.get_pixels_on_line(int(x1), int(y1),
                                          int(x2), int(y2))
        return numpy.array(values)

    def _plotpoints(self, obj, color):

        image = self.fitsimage.get_image()

        # Get points on the line
        if obj.kind == 'line':
            if self.widthtype == 'none':
                points = image.get_pixels_on_line(int(obj.x1), int(obj.y1),
                                                  int(obj.x2), int(obj.y2))
            else:
                coords = image.get_pixels_on_line(int(obj.x1), int(obj.y1),
                                                  int(obj.x2), int(obj.y2),
                                                  getvalues=False)

                points = []
                for x, y in coords:
                    arr = self.get_orthogonal_array(image, obj, x, y,
                                                       self.width_radius)
                    val = numpy.nansum(arr)
                    points.append(val)

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

        if self.settings.get('show_cuts_legend', False):
            self.add_legend()

    def add_legend(self):
        cuts = [tag for tag in self.tags if tag is not self._new_cut]

        # Shrink plot width by 20%
        box = self.plot.ax.get_position()
        self.plot.ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

        self.plot.ax.legend(cuts, loc='center left', bbox_to_anchor=(1, 0.5),
                            shadow=True, fancybox=True,
                            prop={'size': 8}, labelspacing=0.2)

    def _replot(self, lines, colors):
        for idx in range(len(lines)):
            line, color = lines[idx], colors[idx]
            line.color = color
            self._plotpoints(line, color)

        return True

    def replot_all(self):
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
            self._replot(lines, colors)
            if n:
                self.w.delete_cut.set_enabled(True)
                self.w.delete_all.set_enabled(True)
                self.save_btn.set_enabled(True)

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

    def _update_tines(self, obj):
        if obj.objects[0].kind != 'line':
            # right now we only know how to adjust lines
            return

        # Remove previous tines, if any
        if len(obj.objects) > 2:
            obj.objects = obj.objects[:2]

        if self.widthtype == 'none':
            return

        image = self.fitsimage.get_image()
        line = obj.objects[0]
        coords = image.get_pixels_on_line(int(line.x1), int(line.y1),
                                          int(line.x2), int(line.y2),
                                          getvalues=False)
        crdmap = OffsetMapper(self.fitsimage, line)
        num_ticks = max(len(coords) // self.tine_spacing_px, 3)
        interval = len(coords) // num_ticks
        for i in range(0, len(coords), interval):
            x, y = coords[i]
            x1, y1, x2, y2 = self.get_orthogonal_points(line, x, y,
                                                        self.width_radius)
            (x1, y1), (x2, y2) = crdmap.calc_offsets([(x1, y1), (x2, y2)])
            aline = self.dc.Line(x1, y1, x2, y2)
            aline.crdmap = crdmap
            aline.editable = False
            obj.objects.append(aline)

    def _create_cut_obj(self, count, cuts_obj, color='cyan'):
        text = "cuts%d" % (count)
        if not self.settings.get('label_cuts', False):
            text = ''
        cuts_obj.showcap = False
        cuts_obj.linestyle = 'solid'
        #cuts_obj.color = color
        color = cuts_obj.color
        args = [cuts_obj]
        text_obj = self.dc.Text(4, 4, text, color=color, coord='offset',
                                ref_obj=cuts_obj)
        args.append(text_obj)

        obj = self.dc.CompoundObject(*args)
        obj.set_data(cuts=True)

        if (self.widthtype != 'none') and (self.width_radius > 0):
            self._update_tines(obj)
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
            #return self._append_lists(list(map(self._getlines, obj.objects)))
            return [ obj.objects[0] ]
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

        self.replot_all()
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
                self.canvas.deleteObjectByTag(self.cutstag)
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
            self._update_tines(cut)
            cuts.append(cut)

        if len(cuts) == 1:
            cut = cuts[0]
        else:
            cut = self._combine_cuts(*cuts)

        cut.set_data(count=count)

        self.canvas.deleteObjectByTag(tag)
        self.canvas.add(cut, tag=tag)
        self.add_cuts_tag(tag)

        self.logger.debug("redoing cut plots")
        return self.replot_all()

    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        canvas.deleteObjectByTag(tag)

        if not obj.kind in self.cuttypes:
            return True

        count = self._get_cut_index()
        tag = "cuts%d" % (count)

        cut = self._create_cut_obj(count, obj, color='cyan')
        cut.set_data(count=count)
        self._update_tines(cut)

        canvas.deleteObjectByTag(tag)
        self.canvas.add(cut, tag=tag)
        self.add_cuts_tag(tag)

        self.logger.debug("redoing cut plots")
        return self.replot_all()

    def edit_cb(self, canvas, obj):
        self.redraw_cuts()
        self.replot_all()
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

    def set_mode_cb(self, mode, tf):
        """Called when one of the Move/Draw/Edit radio buttons is selected.
        """
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_select_cuts()
        return True

    def set_mode(self, mode):
        self.canvas.set_draw_mode(mode)
        self.w.btn_move.set_state(mode == 'move')
        self.w.btn_draw.set_state(mode == 'draw')
        self.w.btn_edit.set_state(mode == 'edit')

    def redraw_cuts(self):
        """Redraws cuts with tines (for cuts with a 'width')."""
        self.logger.debug("redrawing cuts")
        for cutstag in self.tags:
            if cutstag == self._new_cut:
                continue
            obj = self.canvas.getObjectByTag(cutstag)
            if obj.kind != 'compound':
                continue
            self._update_tines(obj)
        self.canvas.redraw(whence=3)

    def width_radius_changed_cb(self, widget, val):
        """Callback executed when the Width radius is changed."""
        self.width_radius = val
        self.redraw_cuts()
        self.replot_all()
        return True

    def set_width_type_cb(self, widget, idx):
        self.widthtype = self.widthtypes[idx]
        self.redraw_cuts()
        self.replot_all()
        return True

    def save_cb(self):
        fig, xarr, yarr = self.plot.get_data()

        target = Widgets.SaveDialog(title='Save plot', selectedfilter='*.png').get_path()
        with open(target, 'w') as target_file:
            fig.savefig(target_file, dpi=100, format='png', bbox_inches='tight')

        target = Widgets.SaveDialog(title='Save data', selectedfilter='*.npz').get_path()
        with open(target, 'w') as target_file:
            numpy.savez_compressed(target_file, x=xarr, y=yarr)

    def __str__(self):
        return 'cuts'

#END
