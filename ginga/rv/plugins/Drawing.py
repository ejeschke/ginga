# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
A plugin for drawing canvas forms (overlaid graphics).

**Plugin Type: Local**

``Drawing`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

This plugin can be used to draw many different shapes on the image display.
When it is in "draw" mode, select a shape from the drop-down menu, adjust
the shape's parameters (if needed), and draw on the image by using left
mouse button. You can choose to draw in pixel or WCS space.

To move or edit an existing shape, set the plugin on "edit" or "move" mode,
respectively.

To save the drawn shape(s) as mask image, click the "Create Mask" button
and you will see a new mask image created in Ginga. Then, use ``SaveImage``
plugin to save it out as single-extension FITS. Note that the mask will
take the size of the displayed image. Therefore, to create masks for
different image dimensions, you need to repeat the steps multiple times.

Shapes drawn on the canvas can be loaded and/or saved in astropy-regions
(compatible with DS9 regions) format.  To use that you need to have
installed the astropy-regions package.  Simply draw objects on the canvas,
with coords as "data" (pixel) or "wcs".  Note that not all Ginga canvas
objects can be converted to regions shapes and some attributes may not
be saved, may be ignored or may cause errors trying to load the regions
shapes in other software.
"""
from datetime import datetime

from ginga import GingaPlugin
from ginga import colors
from ginga.gw import Widgets
from ginga.misc import ParamSet, Bunch
from ginga.util import dp, ap_region
from ginga.canvas.CanvasObject import coord_names

__all__ = ['Drawing']

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

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('point', color='cyan')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_callback('edit-select', self.edit_select_cb)
        canvas.set_surface(self.fitsimage)
        # So we can draw and edit with the cursor
        canvas.register_for_cursor_drawing(self.fitsimage)
        self.canvas = canvas

        # get Drawing preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Drawing')
        self.settings.add_defaults(orientation=None)
        self.settings.load(onError='silent')

        self.drawtypes = list(canvas.get_drawtypes())
        self.drawcolors = draw_colors
        self.linestyles = ['solid', 'dash']
        self.coordtypes = coord_names
        # contains all parameters to be passed to the constructor
        self.draw_args = []
        self.draw_kwdargs = {}
        # cache of all canvas item parameters
        self.drawparams_cache = {}
        # holds object being edited
        self.edit_obj = None

        # For mask creation from drawn objects
        self._drawn_tags = []
        self._mask_prefix = 'drawing'

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
        self.orientation = orientation
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Drawing")

        captions = (("Draw type:", 'label', "Draw type", 'combobox'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        combobox = b.draw_type
        for name in self.drawtypes:
            combobox.append_text(name)
        index = self.drawtypes.index(default_drawtype)
        combobox.set_index(index)
        combobox.add_callback(
            'activated', lambda w, idx: self.set_drawtype_cb())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Draw")
        btn1.set_state(mode == 'draw')
        btn1.add_callback(
            'activated', lambda w, val: self.set_mode_cb('draw', val))
        btn1.set_tooltip("Choose this to draw")
        self.w.btn_draw = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Edit", group=btn1)
        btn2.set_state(mode == 'edit')
        btn2.add_callback(
            'activated', lambda w, val: self.set_mode_cb('edit', val))
        btn2.set_tooltip("Choose this to edit")
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
                    ("Delete Obj", 'button', "Copy Obj", 'button',
                     "Create mask", 'button', "Clear canvas", 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.delete_obj.add_callback('activated', lambda w: self.delete_object())
        b.delete_obj.set_tooltip("Delete selected object in edit mode")
        b.delete_obj.set_enabled(False)

        b.copy_obj.add_callback('activated', lambda w: self.copy_object())
        b.copy_obj.set_tooltip("Copy selected object in edit mode")
        b.copy_obj.set_enabled(False)

        b.scale_by.add_callback('activated', self.scale_object)
        b.scale_by.set_text('0.9')
        b.scale_by.set_tooltip("Scale selected object in edit mode")
        b.scale_by.set_enabled(False)

        b.rotate_by.add_callback('activated', self.rotate_object)
        b.rotate_by.set_text('90.0')
        b.rotate_by.set_tooltip("Rotate selected object in edit mode")
        b.rotate_by.set_enabled(False)

        b.create_mask.add_callback('activated', lambda w: self.create_mask())
        b.create_mask.set_tooltip("Create boolean mask from drawing")
        b.clear_canvas.add_callback('activated', lambda w: self.clear_canvas())
        b.clear_canvas.set_tooltip("Delete all drawing objects")

        vbox.add_widget(w, stretch=0)

        captions = (("Import regions", 'button', "Export regions", 'button',
                     'reg_format', 'combobox'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.import_regions.add_callback('activated', self.import_regions_cb)
        b.import_regions.set_tooltip("Load a regions file")
        b.import_regions.set_enabled(ap_region.HAVE_REGIONS)
        b.export_regions.add_callback('activated', self.export_regions_cb)
        b.export_regions.set_tooltip("Save a regions file")
        b.export_regions.set_enabled(ap_region.HAVE_REGIONS)

        if ap_region.HAVE_REGIONS:
            for fmt in ap_region.regions.Regions.get_formats()['Format']:
                b.reg_format.append_text(fmt)
        else:
            b.reg_format.set_enabled(False)
        b.reg_format.set_tooltip("Select format for regions output file")

        vbox.add_widget(w, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.toggle_create_button()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))

    def start(self):
        self.set_drawparams_cb()

        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status("Draw a figure with the right mouse button")

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        # don't leave us stuck in edit mode
        self.canvas.set_draw_mode('draw')
        self.canvas.ui_set_active(False)
        self.fv.show_status("")

    def redo(self):
        pass

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        self._drawn_tags.append(tag)
        self.toggle_create_button()
        self.logger.info("drew a %s" % (obj.kind))
        return True

    def set_drawtype_cb(self):
        if self.canvas.get_draw_mode() != 'draw':
            self.canvas.set_draw_mode('draw')
        self.w.btn_draw.set_state(True)
        self.set_mode_cb('draw', True)

    def set_drawparams_cb(self):
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]

        # remove old params
        self.w.drawvbox.remove_all()

        # Create new drawing class of the right kind
        drawClass = self.canvas.get_draw_class(kind)

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
        self.w.copy_obj.set_enabled(False)
        self.w.scale_by.set_enabled(False)
        self.w.rotate_by.set_enabled(False)

        args, kwdargs = self.draw_params.get_params()
        self.logger.debug("changing params to: %s" % (str(kwdargs)))
        self.canvas.set_drawtype(kind, **kwdargs)

    def draw_params_changed_cb(self, paramObj, params):
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]

        args, kwdargs = self.draw_params.get_params()
        self.logger.debug("changing params to: %s" % (str(kwdargs)))
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
                self.logger.debug(
                    "coordmap has changed to '%s'--"
                    "converting mapper" % (str(tomap)))
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
            self.draw_params.add_callback(
                'changed', self.edit_params_changed_cb)

            self.w.drawvbox.add_widget(w, stretch=1)
            self.w.delete_obj.set_enabled(True)
            self.w.copy_obj.set_enabled(True)
            self.w.scale_by.set_enabled(True)
            self.w.rotate_by.set_enabled(True)
        else:
            self.w.attrlbl.set_text("")

            self.w.delete_obj.set_enabled(False)
            self.w.copy_obj.set_enabled(False)
            self.w.scale_by.set_enabled(False)
            self.w.rotate_by.set_enabled(False)

    def edit_select_cb(self, fitsimage, obj):
        self.logger.debug(
            "editing selection status has changed for %s" % str(obj))
        self.edit_initialize(fitsimage, obj)

    def set_mode_cb(self, mode, tf):
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_initialize(self.fitsimage, None)
            elif mode == 'draw':
                self.set_drawparams_cb()
        return True

    def toggle_create_button(self):
        """Enable or disable Create Mask button based on drawn objects."""
        if len(self._drawn_tags) > 0:
            self.w.create_mask.set_enabled(True)
        else:
            self.w.create_mask.set_enabled(False)

    def create_mask(self):
        """Create boolean mask from drawing.

        All areas enclosed by all the shapes drawn will be set to 1 (True)
        in the mask. Otherwise, the values will be set to 0 (False).
        The mask will be inserted as a new image buffer, like ``Mosaic``.

        """
        ntags = len(self._drawn_tags)

        if ntags == 0:
            return

        old_image = self.fitsimage.get_image()

        if old_image is None:
            return

        mask = None
        obj_kinds = set()

        # Create mask
        for tag in self._drawn_tags:
            obj = self.canvas.get_object_by_tag(tag)

            try:
                cur_mask = old_image.get_shape_mask(obj)
            except Exception as e:
                self.logger.error('Cannot create mask: {0}'.format(str(e)))
                continue

            if mask is not None:
                mask |= cur_mask
            else:
                mask = cur_mask

            obj_kinds.add(obj.kind)

        # Might be useful to inherit header from displayed image (e.g., WCS)
        # but the displayed image should not be modified.
        # Bool needs to be converted to int so FITS writer would not crash.
        image = dp.make_image(mask.astype('int16'), old_image, {},
                              pfx=self._mask_prefix)
        imname = image.get('name')

        # Insert new image
        self.fv.gui_call(self.fv.add_image, imname, image, chname=self.chname)

        # Add description to ChangeHistory
        s = 'Mask created from {0} drawings ({1})'.format(
            ntags, ','.join(sorted(obj_kinds)))
        info = dict(time_modified=datetime.utcnow(), reason_modified=s)
        self.fv.update_image_info(image, info)
        self.logger.info(s)

    def clear_canvas(self):
        self.canvas.clear_selected()
        self.canvas.delete_all_objects()
        self._drawn_tags = []
        self.toggle_create_button()

    def delete_object(self):
        tag = self.canvas.lookup_object_tag(self.canvas._edit_obj)
        if tag in self._drawn_tags:
            self._drawn_tags.remove(tag)
        self.toggle_create_button()
        self.canvas.edit_delete()
        self.canvas.redraw(whence=2)

    def copy_object(self):
        obj = self.canvas._edit_obj.copy()
        tag = self.canvas.add(obj)
        obj.move_delta_pt((20, 20))
        self._drawn_tags.append(tag)
        self.canvas.redraw(whence=2)

    def rotate_object(self, w):
        delta = float(w.get_text())
        self.canvas.edit_rotate(delta, self.fitsimage)

    def scale_object(self, w):
        delta = float(w.get_text())
        self.canvas.edit_scale(delta, delta, self.fitsimage)

    def import_regions_cb(self, w):
        if not ap_region.HAVE_REGIONS:
            self.fv.show_error("Please install astropy regions to use this",
                               raisetab=True)
            return
        from ginga.gw.GwHelp import FileSelection
        fs = FileSelection(w.get_widget(), all_at_once=True)
        fs.popup('Load regions file', self._import_regions_files,
                 initialdir='.',
                 filename='Region files (*.reg *.ds9 *.crtf *.fits)')

    def _import_regions_files(self, paths):
        for path in paths:
            objs = ap_region.import_regions(path, logger=self.logger)
            for obj in objs:
                self.canvas.add(obj, redraw=False)

        self.canvas.update_canvas()

    def export_regions_cb(self, w):
        if not ap_region.HAVE_REGIONS:
            self.fv.show_error("Please install astropy regions to use this",
                               raisetab=True)
            return

        fs = Widgets.SaveDialog('Save Regions',
                                selectedfilter='*.reg')
        path = fs.get_path()
        if path is None:
            # cancelled
            return

        regs = ap_region.export_regions_canvas(self.canvas, logger=self.logger)

        format = self.w.reg_format.get_text()

        # dialog above confirms if they want to overwrite, so we can
        # simply use overwrite=True
        regs.write(path, format=format, overwrite=True)

    def __str__(self):
        return 'drawing'

# END
