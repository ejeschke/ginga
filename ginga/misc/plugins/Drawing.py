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
from ginga.misc import Widgets, CanvasTypes, ParamSet, Bunch

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

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('point', color='cyan')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_callback('edit-select', self.edit_select_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        bm = fitsimage.get_bindmap()
        bm.add_callback('mode-set', self.mode_change_cb)

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

        fr = Widgets.Frame("Instructions")
        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
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
        self.tw.set_text("""Draw a figure with the right mouse button.""")
            
    def start(self):
        self.instructions()
        self.set_drawparams_cb()

        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
            
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a figure with the right mouse button")
        
    def stop(self):
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.canvas.ui_setActive(False)
        self.fv.showStatus("")

    def redo(self):
        pass

    def draw_cb(self, fitsimage, tag):
        # TODO: record information about objects drawn?
        pass

    def set_drawparams_cb(self):
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]
        index = self.w.coord_type.get_index()
        coord = self.coordtypes[index]

        # remove old params
        self.w.drawvbox.remove_all()

        # Create new drawing class of the right kind
        drawClass = self.fitsimage.getDrawClass(kind)

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

        args, kwdargs = self.draw_params.get_params()
        #print("changing params to: %s" % str(kwdargs))
        if kind != 'compass':
            kwdargs['coord'] = coord
        self.canvas.set_drawtype(kind, **kwdargs)

    def draw_params_changed_cb(self, paramObj, params):
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]

        args, kwdargs = self.draw_params.get_params()
        #print("changing params to: %s" % str(kwdargs))
        self.canvas.set_drawtype(kind, **kwdargs)
        
    def edit_cb(self, fitsimage, obj):
        # <-- obj has been edited
        #print("edit event on canvas: obj=%s" % (obj))
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
                #print("coordmap has changed to '%s'--converting mapper" % (
                #    str(tomap)))
                # user changed type of mapper; convert coordinates to
                # new mapper and update widgets
                obj.convert_mapper(tomap)
                paramObj.params_to_widgets()
            
        # TODO: change whence to 0 if allowing editing of images
        whence = 2
        self.canvas.redraw(whence=whence)
        
    def edit_select_cb(self, fitsimage, obj):
        #print("editing selection status has changed for %s" % str(obj))
        if obj != self.edit_obj:
            # edit object is new.  Update visual parameters

            # remove old params
            self.w.drawvbox.remove_all()

            self.edit_obj = obj
            if obj is not None:
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

    def mode_change_cb(self, bindmap, modename, modetype):
        if modename == 'draw':
            self.set_drawparams_cb()
        elif modename == 'edit':
            obj = self.canvas.get_edit_object()
            self.edit_select_cb(self.fitsimage, obj)
        else:
            self.edit_select_cb(self.fitsimage, None)
        
    def clear_canvas(self):
        self.canvas.deleteAllObjects()
        
    def delete_object(self):
        self.canvas.edit_delete()
        self.canvas.redraw(whence=2)
        
    def rotate_object(self, w):
        delta = float(w.get_text())
        self.canvas.edit_rotate(delta)
        
    def scale_object(self, w):
        delta = float(w.get_text())
        self.canvas.edit_scale(delta, delta)
        
    def __str__(self):
        return 'drawing'
    
#END
