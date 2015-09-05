#
# Drawing.py -- Drawing plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga import colors
from ginga.gw import Widgets
from ginga.misc import ParamSet, Bunch

draw_colors = colors.get_colors()

default_drawtype = 'circle'
default_drawcolor = 'lightblue'
fillkinds = ('circle', 'rectangle', 'polygon', 'triangle', 'righttriangle',
             'square', 'ellipse', 'box')

class Drawing(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Drawing, self).__init__(fv, fitsimage)

        self.layertag = 'drawing-canvas'

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('point', color='cyan')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_callback('edit-select', self.edit_select_cb)
        canvas.setSurface(self.fitsimage)
        # So we can draw and edit with the cursor
        canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas = canvas

        self.drawtypes = list(canvas.get_drawtypes())
        self.drawcolors = draw_colors
        self.linestyles = ['solid', 'dash']
        self.coordtypes = ['data', 'wcs']
        # contains all parameters to be passed to the constructor
        self.draw_args = []
        self.draw_kwdargs = {}
        # cache of all canvas item parameters
        self.drawparams_cache = {}
        # holds object being edited
        self.edit_obj = None

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        self.orientation = orientation
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msgFont)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Drawing")

        captions = (("Draw type:", 'label', "Draw type", 'combobox'),
                    ("Coord type:", 'label', "Coord type", 'combobox'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        combobox = b.draw_type
        for name in self.drawtypes:
            combobox.append_text(name)
        index = self.drawtypes.index(default_drawtype)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams_cb())

        combobox = b.coord_type
        for name in self.coordtypes:
            combobox.append_text(name)
        index = 0
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams_cb())

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

        fr = Widgets.Frame("Attributes")
        vbox2 = Widgets.VBox()
        self.w.attrlbl = Widgets.Label()
        vbox2.add_widget(self.w.attrlbl, stretch=0)
        self.w.drawvbox = Widgets.VBox()
        vbox2.add_widget(self.w.drawvbox, stretch=1)
        fr.set_widget(vbox2)

        vbox.add_widget(fr, stretch=0)

        captions = (("Rotate By:", 'label', 'Rotate By', 'entry',
                     "Scale By:", 'label', 'Scale By', 'entry'),
                    ("Delete Obj", 'button', "sp1", 'spacer',
                     "sp2", 'spacer', "Clear canvas", 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.delete_obj.add_callback('activated', lambda w: self.delete_object())
        b.delete_obj.set_tooltip("Delete selected object in edit mode")
        b.delete_obj.set_enabled(False)
        b.scale_by.add_callback('activated', self.scale_object)
        b.scale_by.set_text('0.9')
        b.scale_by.set_tooltip("Scale selected object in edit mode")
        b.scale_by.set_enabled(False)
        b.rotate_by.add_callback('activated', self.rotate_object)
        b.rotate_by.set_text('90.0')
        b.rotate_by.set_tooltip("Rotate selected object in edit mode")
        b.rotate_by.set_enabled(False)
        b.clear_canvas.add_callback('activated', lambda w: self.clear_canvas())
        b.clear_canvas.set_tooltip("Delete all drawing objects")

        vbox.add_widget(w, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)


    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))

    def instructions(self):
        self.tw.set_text(
            """Draw a figure with the cursor.

For polygons/paths press 'v' to create a vertex, 'z' to remove last vertex.""")

    def start(self):
        self.instructions()
        self.set_drawparams_cb()

        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a figure with the right mouse button")

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.deleteObjectByTag(self.layertag)
        except:
            pass
        # don't leave us stuck in edit mode
        self.canvas.set_draw_mode('draw')
        self.canvas.ui_setActive(False)
        self.fv.showStatus("")

    def redo(self):
        pass

    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        self.logger.info("drew a %s" % (obj.kind))
        return True

    def set_drawparams_cb(self):
        if self.canvas.get_draw_mode() != 'draw':
            # if we are in edit mode then don't initialize draw gui
            return
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]
        index = self.w.coord_type.get_index()
        coord = self.coordtypes[index]

        # remove old params
        self.w.drawvbox.remove_all()

        # Create new drawing class of the right kind
        drawClass = self.canvas.getDrawClass(kind)

        self.w.attrlbl.set_text("New Object: %s" % (kind))
        # Build up a set of control widgets for the parameters
        # of the canvas object to be drawn
        paramlst = drawClass.get_params_metadata()

        params = self.drawparams_cache.setdefault(kind, Bunch.Bunch())
        self.draw_params = ParamSet.ParamSet(self.logger, params)

        w = self.draw_params.build_params(paramlst,
                                          orientation=self.orientation)
        self.draw_params.add_callback('changed', self.draw_params_changed_cb)

        self.w.drawvbox.add_widget(w, stretch=1)

        # disable edit-only controls
        self.w.delete_obj.set_enabled(False)
        self.w.scale_by.set_enabled(False)
        self.w.rotate_by.set_enabled(False)

        args, kwdargs = self.draw_params.get_params()
        #self.logger.debug("changing params to: %s" % str(kwdargs))
        if kind != 'compass':
            kwdargs['coord'] = coord
        self.canvas.set_drawtype(kind, **kwdargs)

    def draw_params_changed_cb(self, paramObj, params):
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]

        args, kwdargs = self.draw_params.get_params()
        #self.logger.debug("changing params to: %s" % str(kwdargs))
        self.canvas.set_drawtype(kind, **kwdargs)

    def edit_cb(self, fitsimage, obj):
        # <-- obj has been edited
        #self.logger.debug("edit event on canvas: obj=%s" % (obj))
        if obj != self.edit_obj:
            # edit object is new.  Update visual parameters
            self.edit_select_cb(fitsimage, obj)
        else:
            # edit object has been modified.  Sync visual parameters
            self.draw_params.params_to_widgets()

    def edit_params_changed_cb(self, paramObj, obj):
        self.draw_params.widgets_to_params()
        if hasattr(obj, 'coord'):
            tomap = self.fitsimage.get_coordmap(obj.coord)
            if obj.crdmap != tomap:
                #self.logger.debug("coordmap has changed to '%s'--converting mapper" % (
                #    str(tomap)))
                # user changed type of mapper; convert coordinates to
                # new mapper and update widgets
                obj.convert_mapper(tomap)
                paramObj.params_to_widgets()

        obj.sync_state()
        # TODO: change whence to 0 if allowing editing of images
        whence = 2
        self.canvas.redraw(whence=whence)

    def edit_initialize(self, fitsimage, obj):
        # remove old params
        self.w.drawvbox.remove_all()

        self.edit_obj = obj
        if (obj is not None) and self.canvas.is_selected(obj):
            self.w.attrlbl.set_text("Editing a %s" % (obj.kind))

            drawClass = obj.__class__

            # Build up a set of control widgets for the parameters
            # of the canvas object to be drawn
            paramlst = drawClass.get_params_metadata()

            self.draw_params = ParamSet.ParamSet(self.logger, obj)

            w = self.draw_params.build_params(paramlst,
                                              orientation=self.orientation)
            self.draw_params.add_callback('changed', self.edit_params_changed_cb)

            self.w.drawvbox.add_widget(w, stretch=1)
            self.w.delete_obj.set_enabled(True)
            self.w.scale_by.set_enabled(True)
            self.w.rotate_by.set_enabled(True)
        else:
            self.w.attrlbl.set_text("")

            self.w.delete_obj.set_enabled(False)
            self.w.scale_by.set_enabled(False)
            self.w.rotate_by.set_enabled(False)

    def edit_select_cb(self, fitsimage, obj):
        self.logger.debug("editing selection status has changed for %s" % str(obj))
        self.edit_initialize(fitsimage, obj)

    def set_mode_cb(self, mode, tf):
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_initialize(self.fitsimage, None)
            elif mode == 'draw':
                self.set_drawparams_cb()
        return True

    def clear_canvas(self):
        self.canvas.clear_selected()
        self.canvas.deleteAllObjects()

    def delete_object(self):
        self.canvas.edit_delete()
        self.canvas.redraw(whence=2)

    def rotate_object(self, w):
        delta = float(w.get_text())
        self.canvas.edit_rotate(delta, self.fitsimage)

    def scale_object(self, w):
        delta = float(w.get_text())
        self.canvas.edit_scale(delta, delta, self.fitsimage)

    def __str__(self):
        return 'drawing'

#END
