# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Ruler`` is a simple plugin designed to measure distances on an image.

**Plugin Type: Local**

``Ruler`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

``Ruler`` measures distance by calculating a spherical triangulation
via WCS mapping of three points defined by a single line drawn on the image.
By default, the distance is shown in arcminutes of sky, but using the
"Units" control, it can be changed to show degrees or pixel distance instead.

Click and drag to establish a ruler between two points.  When you finish
the draw operation the ruler is established and the plugin UI will update
to show detail about the line, including the endpoint positions and the
angle of the line.  The units of the angle can be toggled between degrees
and radians using the adjacent drop-down box.

To erase the old and make a new ruler, click and drag again.
When another line is drawn, it replaces the first one.
When the plugin is closed, the graphic overlay is removed.
Should you want "sticky rulers", use the ``Drawing`` plugin
(and choose "Ruler" as the drawing type).

**Editing**

To edit an existing ruler, click the radio button in the plugin
UI labeled "Edit".  If the ruler does not become selected
immediately, click on the diagonal connecting the two points.
This should establish a bounding box around the ruler and show its
control points.  Drag within the bounding box to move the ruler or
click and drag the endpoints to edit the ruler.  The ruler can also
be scaled or rotated using those control points.

**UI**

The units shown for distance can be selected from the drop-down box
in the UI.  You have a choice of "arcmin", "degrees", or "pixels".
The first two require a valid and working WCS in the image.

The endpoint values are shown in the UI, but can additionally be shown
in the ruler graphic if the "Show ends" checkbox is toggled.  Plumb
lines will be shown if the "Show plumb" box is toggled.

**Buttons**

The "Pan to src" button will pan the main image to the origin of the
line drawn, while "Pan to dst" will pan to the end.  "Pan to ctr" sets
the pan position to the center point of the line.  These buttons may be
useful for close up, zoomed-in work on the image.  "Clear" clears the
ruler from the image.

**Tips**
Open the "Zoom" plugin to precisely see detail of the cursor area (the
graphics of the ruler are not shown there, however).
The "Pick" plugin can also be used in conjunction with Ruler to identify
the central point of an object, when aligning either end of the ruler.

"""
import numpy as np

from ginga import GingaPlugin
from ginga.gw import Widgets

__all__ = ['Ruler']


class Ruler(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Ruler, self).__init__(fv, fitsimage)

        # get Ruler preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Ruler')
        self.settings.add_defaults(show_plumb=True, show_ends=True,
                                   rule_color='green', draw_color='cyan',
                                   units='arcmin', angle_unit='degrees')
        self.settings.load(onError='silent')

        self.layertag = 'ruler-canvas'
        self.ruletag = None
        self.w = None
        self.unittypes = ('arcmin', 'degrees', 'pixels')
        self.ang_units = ('degrees', 'radians')

        self.rulecolor = self.settings.get('rule_color', 'green')
        self.drawcolor = self.settings.get('draw_color', 'cyan')
        self.units = self.settings.get('units', 'arcmin')
        self.ang_unit = self.settings.get('angle_unit', 'degrees')
        self.show_ends = self.settings.get('show_ends', True)
        self.show_plumb = self.settings.get('show_plumb', True)

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('ruler')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('draw-down', self.clear_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_draw_mode('draw')
        canvas.set_surface(self.fitsimage)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.name = 'Ruler-canvas'
        self.canvas = canvas

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Ruler")

        captions = (("Units:", 'label', 'Units', 'combobox'),
                    ("Show ends", 'checkbutton', "Show plumb", 'checkbutton'),
                    ("Pan to src", 'button', "Pan to dst", 'button'),
                    ("Pan to ctr", 'button', "Clear", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        combobox = b.units
        for name in self.unittypes:
            combobox.append_text(name)
        index = self.unittypes.index(self.units)
        combobox.set_index(index)
        combobox.set_tooltip("What units to show the measurements")
        combobox.add_callback('activated', lambda w, idx: self.set_units())

        b.show_ends.add_callback('activated', self.show_ends_cb)
        b.show_ends.set_tooltip("Show end points on ruler")
        b.show_ends.set_state(self.show_ends)
        b.show_plumb.add_callback('activated', self.show_plumb_cb)
        b.show_plumb.set_tooltip("Show plumb lines on ruler")
        b.show_plumb.set_state(self.show_plumb)

        have_ruler = self.ruletag is not None
        b.pan_to_src.add_callback('activated', self.pan_cb, 'src')
        b.pan_to_src.set_tooltip("Pan to start position")
        b.pan_to_src.set_enabled(have_ruler)
        b.pan_to_dst.add_callback('activated', self.pan_cb, 'dst')
        b.pan_to_dst.set_tooltip("Pan to end position")
        b.pan_to_dst.set_enabled(have_ruler)
        b.pan_to_ctr.add_callback('activated', self.pan_cb, 'ctr')
        b.pan_to_ctr.set_tooltip("Pan to center position")
        b.pan_to_ctr.set_enabled(have_ruler)
        b.clear.add_callback('activated', lambda w: self.clear())
        b.clear.set_tooltip("Clear the ruler")

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Result")

        captions = (("X1:", 'label', 'x1', 'entry',
                     "Y1:", 'label', 'y1', 'entry'),
                    ("X2:", 'label', 'x2', 'entry',
                     "Y2:", 'label', 'y2', 'entry'),
                    ("dx:", 'label', 'dx', 'entry',
                     "dy:", 'label', 'dy', 'entry',
                     "dh:", 'label', 'dh', 'entry'),
                    ("sp1", 'spacer', "degrad", 'combobox',
                     u"\u03B8:", 'label', "theta", 'entry'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        combobox = b.degrad
        for name in self.ang_units:
            combobox.append_text(name)
        index = self.ang_units.index(self.ang_unit)
        combobox.set_index(index)
        combobox.set_tooltip("What units to show the angle")
        combobox.add_callback('activated', lambda w, idx: self.set_angle_units())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Draw")
        btn1.set_state(mode == 'draw')
        btn1.add_callback(
            'activated', lambda w, val: self.set_mode_cb('draw', val))
        btn1.set_tooltip("Choose this to draw a ruler")
        self.w.btn_draw = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Edit", group=btn1)
        btn2.set_state(mode == 'edit')
        btn2.add_callback(
            'activated', lambda w, val: self.set_mode_cb('edit', val))
        btn2.set_tooltip("Choose this to edit a ruler")
        self.w.btn_edit = btn2
        hbox.add_widget(btn2)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

    def _setup_draw(self):
        self.canvas.set_drawtype('ruler', color=self.drawcolor,
                                 units=self.units,
                                 showends=self.show_ends,
                                 showplumb=self.show_plumb)

    def set_units(self):
        index = self.w.units.get_index()
        units = self.unittypes[index]
        self.units = units
        self._setup_draw()

        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            if obj.kind == 'ruler':
                obj.units = units
                self.redo()
        return True

    def set_angle_units(self):
        index = self.w.degrad.get_index()
        unit = self.ang_units[index]
        self.ang_unit = unit

        if self.ruletag is not None:
            self.redo()
        return True

    def show_ends_cb(self, w, tf):
        self.show_ends = tf
        self._setup_draw()
        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            if obj.kind == 'ruler':
                obj.showends = tf
                self.redo()
        return True

    def show_plumb_cb(self, w, tf):
        self.show_plumb = tf
        self._setup_draw()
        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            if obj.kind == 'ruler':
                obj.showplumb = tf
                self.redo()
        return True

    def pan_cb(self, w, which):
        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            if obj.kind == 'ruler':
                if which == 'src':
                    x, y = obj.x1, obj.y1
                elif which == 'dst':
                    x, y = obj.x2, obj.y2
                else:
                    x, y = obj.get_center_pt()[:2]

                self.fitsimage.set_pan(x, y)

    def pan_src_cb(self, w):
        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            if obj.kind == 'ruler':
                x, y = obj.x1, obj.y1
                self.fitsimage.set_pan(x, y)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def _ui_sanity_check(self):
        have_ruler = self.ruletag is not None
        self.w.pan_to_src.set_enabled(have_ruler)
        self.w.pan_to_dst.set_enabled(have_ruler)
        self.w.pan_to_ctr.set_enabled(have_ruler)

        # clear result boxes
        self.w.x1.set_text('')
        self.w.y1.set_text('')
        self.w.x2.set_text('')
        self.w.y2.set_text('')
        self.w.dh.set_text('')
        self.w.dx.set_text('')
        self.w.dy.set_text('')
        self.w.theta.set_text('')

        if have_ruler:
            self.redo()

    def start(self):
        # start ruler drawing operation
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag=self.layertag)

        #self.clear()
        self._setup_draw()
        self.resume()
        self._ui_sanity_check()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status("Draw a ruler with the right mouse button")

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.canvas.ui_set_active(False)
        self.fv.show_status("")

    def redo(self):
        obj = self.canvas.get_object_by_tag(self.ruletag)
        if obj.kind != 'ruler':
            return True

        # set results table
        text = obj.get_ruler_distances(self.fitsimage)
        x1, y1 = text.b.split(',')
        self.w.x1.set_text(x1.strip())
        self.w.y1.set_text(y1.strip())
        x2, y2 = text.e.split(',')
        self.w.x2.set_text(x2.strip())
        self.w.y2.set_text(y2.strip())
        self.w.dh.set_text(text.h)
        self.w.dx.set_text(text.x)
        self.w.dy.set_text(text.y)

        res = text.res
        if self.ang_unit == 'degrees':
            ang_s = "%.5f" % (np.degrees(res.theta))
        else:
            ang_s = "%.5f" % (res.theta)
        self.w.theta.set_text(ang_s)

        # redraw updates ruler measurements
        self.canvas.redraw(whence=3)

    def clear(self):
        self.canvas.clear_selected()
        try:
            self.canvas.delete_object_by_tag(self.ruletag)
        except Exception:
            pass
        self.ruletag = None
        self._ui_sanity_check()

    def clear_cb(self, canvas, button, data_x, data_y):
        self.clear()
        return False

    def draw_cb(self, surface, tag):
        obj = self.canvas.get_object_by_tag(tag)
        if obj.kind != 'ruler':
            return True
        # remove the old ruler
        try:
            self.canvas.delete_object_by_tag(self.ruletag)
        except Exception:
            pass

        # change some characteristics of the drawn image and
        # save as the new ruler
        self.ruletag = tag
        obj.color = self.rulecolor
        obj.cap = 'ball'

        self._ui_sanity_check()

    def edit_cb(self, canvas, obj):
        self._ui_sanity_check()
        return True

    def edit_select_ruler(self):
        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            self.canvas.edit_select(obj)
        else:
            self.canvas.clear_selected()
        self.canvas.update_canvas()

    def set_mode_cb(self, mode, tf):
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_select_ruler()
        return True

    def __str__(self):
        return 'ruler'

# END
