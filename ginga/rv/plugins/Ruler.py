#
# Ruler.py -- Ruler plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.gw import Widgets

class Ruler(GingaPlugin.LocalPlugin):
    """
    Ruler
    =====
    Ruler is a simple plugin designed to measure distances on an image.
    It does this by calculating a spherical triangulation via WCS mapping
    of three points defined by a single line drawn on the image.  By default,
    the distance is shown in arcminutes of sky, but using the Units control
    it can be changed to show degrees or pixel distance instead.

    [ Should you want "sticky rulers", use the Drawing plugin (and choose
    "Ruler" as the drawing type). ]

    Plugin Type: Local
    ------------------
    Ruler is a local plugin, which means it is associated with a channel.
    An instance can be opened for each channel.

    Usage
    -----
    Click and drag to establish a ruler between two points.

    Display the Zoom tab at the same time to precisely see detail
    while drawing the ruler, if desired.

    To erase the old and make a new ruler, click and drag again.

    Editing
    -------
    To edit an existing ruler, click the radio button in the plugin
    UI labeled 'Edit'.  If the ruler does not become selected
    immediately, click on it.  Then click and drag the points to edit
    the ruler.

    Units
    -----
    The units shown for distance can be selected from the drop-down box
    in the UI.  You have a choice of 'arcmin', 'degrees' or 'pixels'.
    The first two require a valid and working WCS in the image.
    """
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Ruler, self).__init__(fv, fitsimage)

        self.rulecolor = 'green'
        self.layertag = 'ruler-canvas'
        self.ruletag = None

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('ruler', color='cyan')
        canvas.set_callback('draw-event', self.wcsruler)
        canvas.set_callback('draw-down', self.clear)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_draw_mode('draw')
        canvas.set_surface(self.fitsimage)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.name = 'Ruler-canvas'
        self.canvas = canvas

        self.w = None
        self.unittypes = ('arcmin', 'degrees', 'pixels')
        self.units = 'arcmin'

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Ruler")

        captions = (('Units:', 'label', 'Units', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        combobox = b.units
        for name in self.unittypes:
            combobox.append_text(name)
        index = self.unittypes.index(self.units)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_units())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Draw")
        btn1.set_state(mode == 'draw')
        btn1.add_callback('activated', lambda w, val: self.set_mode_cb('draw', val))
        btn1.set_tooltip("Choose this to draw a ruler")
        self.w.btn_draw = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Edit", group=btn1)
        btn2.set_state(mode == 'edit')
        btn2.add_callback('activated', lambda w, val: self.set_mode_cb('edit', val))
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

    def set_units(self):
        index = self.w.units.get_index()
        units = self.unittypes[index]
        self.units = units
        self.canvas.set_drawtype('ruler', color='cyan', units=units)

        if self.ruletag is not None:
            obj = self.canvas.get_object_by_tag(self.ruletag)
            if obj.kind == 'ruler':
                obj.units = units
                self.canvas.redraw(whence=3)
        return True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # start ruler drawing operation
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag=self.layertag)

        self.canvas.delete_all_objects()
        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True)
        self.fv.show_status("Draw a ruler with the right mouse button")

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass
        self.canvas.ui_set_active(False)
        self.fv.show_status("")

    def redo(self):
        obj = self.canvas.get_object_by_tag(self.ruletag)
        if obj.kind != 'ruler':
            return True
        # redraw updates ruler measurements
        self.canvas.redraw(whence=3)

    def clear(self, canvas, button, data_x, data_y):
        self.canvas.delete_all_objects()
        self.ruletag = None
        return False

    def wcsruler(self, surface, tag):
        obj = self.canvas.get_object_by_tag(tag)
        if obj.kind != 'ruler':
            return True
        # remove the old ruler
        try:
            self.canvas.delete_object_by_tag(self.ruletag)
        except:
            pass

        # change some characteristics of the drawn image and
        # save as the new ruler
        self.ruletag = tag
        obj.color = self.rulecolor
        obj.cap = 'ball'
        self.canvas.redraw(whence=3)

    def edit_cb(self, canvas, obj):
        self.redo()
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

#END
