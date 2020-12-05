# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Capture PNG or JPEG images of the channel viewer image.

**Usage**

1. Select the RGB graphics type for the snap from the "Type" combo box.
2. Press "Snap" when you have the channel image the way you want to capture it.

A copy of the RGB image will be loaded into the ``ScreenShot`` viewer.
You can pan and zoom within the ``ScreenShot`` viewer like a normal Ginga
viewer to examine detail (e.g., see the magnified difference between
JPEG and PNG formats).

3. Repeat (1) and (2) until you have the image you want.
4. Enter a valid path for a new file into the "Folder" text box.
5. Enter a valid name for a new file into the "Name" text box.
   There is no need to add the file extension; it will be added, if needed.
6. Press the "Save" button.  The file will be saved where you specified.

**Notes**

* PNG offers less artifacts for overlaid graphics, but files are larger
  than JPEG.
* The "Center" button will center the snap image; "Fit" will set the
  zoom to fit it to the window; and "Clear" will clear the image.
  Press "Full" to zoom to 100% pixels (1:1 scaling).
* The "Screen size" checkbox (checked by default) will save the image at
  exactly the size of the channel viewer window.  To save at a different
  size, uncheck this box, and set the size via the "Width" and "Height"
  boxes.
* The "Lock aspect" feature only works if "Screen size" is unchecked; if
  enabled, then changing width or height will alter the other parameter
  in order to maintain the aspect ratio shown in the "Aspect" box.

"""
import os.path
import shutil
import tempfile

from ginga import GingaPlugin, trcalc
from ginga.gw import Widgets, Viewers
from ginga.pilw.ImageViewPil import CanvasView
from ginga.util import io_rgb

__all__ = ['ScreenShot']


class ScreenShot(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(ScreenShot, self).__init__(fv, fitsimage)

        self.tosave_type = 'png'
        self.saved_type = None
        self.savetypes = ('png', 'jpeg')
        self.tmpname = os.path.join(tempfile.tempdir, "__snap")
        self.save_path = ''
        self.save_name = ''

        self._wd = 200
        self._ht = 200
        self._split_sizes = [500, 400]

        # Build our screenshot generator
        sg = CanvasView(logger=self.logger)
        sg.configure_surface(self._wd, self._ht)
        sg.enable_autozoom('off')
        sg.enable_autocuts('off')
        sg.enable_autocenter('off')
        sg.enable_auto_orient(False)
        sg.defer_redraw = False
        t_ = self.fitsimage.get_settings()
        sg.t_.set(interpolation=t_.get('interpolation'))
        sg.set_bg(0.7, 0.7, 0.7)
        self.shot_generator = sg
        self.fitsimage.add_callback('configure', self._configure_cb)

        self._screen_size = True
        self._lock_aspect = False
        self._sg_aspect = None
        self._sg_wd = None
        self._sg_ht = None
        self.transfer_attrs = ['transforms', 'rotation', 'cutlevels',
                               'pan', 'rgbmap']
        self.gui_up = False

    def build_gui(self, container):

        vbox = Widgets.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        vbox1 = Widgets.VBox()

        # Uncomment to debug; passing parent logger generates too
        # much noise in the main logger
        #zi = Viewers.CanvasView(logger=self.logger)
        zi = Viewers.CanvasView(logger=None)
        zi.set_desired_size(self._wd, self._ht)
        zi.enable_autozoom('once')
        zi.enable_autocuts('once')
        zi.enable_autocenter('override')
        zi.set_zoom_algorithm('step')
        zi.cut_levels(0, 255)
        zi.transform(False, True, False)
        #zi.set_scale_limits(0.001, 1000.0)
        zi.set_bg(0.4, 0.4, 0.4)
        zi.set_color_map('gray')
        zi.set_intensity_map('ramp')
        # for debugging
        zi.set_name('scrnimage')
        self.scrnimage = zi

        bd = zi.get_bindings()
        bd.enable_zoom(True)
        bd.enable_pan(True)
        bd.enable_cmap(False)
        zi.show_mode_indicator(True)

        iw = Viewers.ScrolledView(zi)
        iw.resize(self._wd, self._ht)
        vbox1.add_widget(iw, stretch=1)

        captions = (
            ('Screen size', 'checkbutton',
             'Width:', 'label', 'width', 'entry',
             'Height:', 'label', 'height', 'entry'),
            ('Lock aspect', 'checkbutton',
             'Aspect:', 'label', 'aspect', 'entry'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w = b

        if self._sg_wd is None:
            wd, ht = self.fitsimage.get_window_size()
            self.shot_generator.configure_surface(wd, ht)
        else:
            wd, ht = self._sg_wd, self._sg_ht

        b.screen_size.set_state(self._screen_size)
        b.screen_size.set_tooltip("From screen viewer actual size")
        b.screen_size.add_callback('activated',
                                   self._screen_size_cb)
        b.lock_aspect.set_state(self._lock_aspect)
        b.lock_aspect.set_tooltip("Lock aspect ratio of screen shot")
        b.lock_aspect.add_callback('activated',
                                   self._lock_aspect_cb)
        b.width.set_text(str(wd))
        b.height.set_text(str(ht))
        b.width.set_enabled(not self._screen_size)
        b.height.set_enabled(not self._screen_size)
        if self._sg_aspect is None:
            _as = trcalc.calc_aspect_str(wd, ht)
            b.aspect.set_text(_as)
        else:
            b.aspect.set_text(str(self._sg_aspect))
        b.aspect.set_enabled(self._lock_aspect)
        b.lock_aspect.set_enabled(not self._screen_size)

        b.width.add_callback('activated',
                             lambda *args: self._set_width_cb())
        b.height.add_callback('activated',
                              lambda *args: self._set_height_cb())
        b.aspect.add_callback('activated', lambda *args: self._set_aspect_cb())

        vbox1.add_widget(w, stretch=0)

        captions = (
            ('Type:', 'label', 'grtype', 'combobox',
             'Snap', 'button'),
            ('Clear', 'button', 'Center', 'button', 'Fit', 'button',
             'Full', 'button'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        combobox = b.grtype
        for name in self.savetypes:
            combobox.append_text(name)
        index = self.savetypes.index(self.tosave_type)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_type(idx))
        combobox.set_tooltip("Set the format of the snap image")

        b.snap.set_tooltip(
            "Click to grab a snapshot of this channel viewer image")
        b.snap.add_callback('activated', self._snap_cb)
        b.clear.set_tooltip("Clear the snap image")
        b.clear.add_callback('activated', self._clear_cb)
        b.center.set_tooltip("Center the snap image")
        b.center.add_callback('activated', self._center_cb)
        b.fit.set_tooltip("Fit snap image to window")
        b.fit.add_callback('activated', self._fit_cb)
        b.full.set_tooltip("View at 100% (1:1)")
        b.full.add_callback('activated', self._full_cb)

        vbox1.add_widget(w, stretch=0)

        fr = Widgets.Frame("Screenshot")
        fr.set_widget(vbox1)

        vpaned = Widgets.Splitter(orientation='vertical')
        self.w.splitter = vpaned
        vpaned.add_widget(fr)
        vpaned.add_widget(Widgets.Label(''))
        vpaned.set_sizes(self._split_sizes)

        vbox2 = Widgets.VBox()

        fr = Widgets.Frame("Save File")

        captions = (('Folder:', 'label', 'folder', 'entry'),
                    ('Name:', 'label', 'name', 'entry'),
                    ('Save', 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.folder.set_text(self.save_path)
        b.folder.set_tooltip("Set the folder path for the snap image")
        b.name.set_text(self.save_name)
        b.name.set_tooltip("Set the name for the snap image")
        b.save.set_tooltip("Click to save the last snap")
        b.save.add_callback('activated', self._save_cb)

        fr.set_widget(w)
        vbox2.add_widget(fr, stretch=0)

        # stretch
        spacer = Widgets.Label('')
        vbox2.add_widget(spacer, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vbox2.add_widget(btns, stretch=0)

        #vpaned.add_widget(vbox2)

        vbox.add_widget(vpaned, stretch=1)

        container.add_widget(vbox, stretch=1)
        container.add_widget(vbox2, stretch=0)
        self.gui_up = True

    def set_type(self, idx):
        self.tosave_type = self.savetypes[idx]
        return True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        pass

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        self.saved_type = None

    def _snap_cb(self, w):
        """This function is called when the user clicks the 'Snap' button.
        """
        # Clear the snap image viewer
        self.scrnimage.clear()
        self.scrnimage.redraw_now(whence=0)
        self.fv.update_pending()

        format = self.tosave_type

        if self._screen_size:
            # snap image using actual viewer
            self.fv.error_wrap(self.fitsimage.save_rgb_image_as_file,
                               self.tmpname, format=format)

        else:
            # we will be using shot generator, not actual viewer.
            # check that shot generator size matches UI params
            self.check_and_adjust_dimensions()

            # copy background color of viewer to shot generator
            bg = self.fitsimage.get_bg()
            self.shot_generator.set_bg(*bg)

            # add the main canvas from channel viewer to shot generator
            c1 = self.fitsimage.get_canvas()
            c2 = self.shot_generator.get_canvas()
            c2.delete_all_objects(redraw=False)
            c2.add(c1, redraw=False)
            # hack to fix a few problem graphics
            self.shot_generator._imgobj = self.fitsimage._imgobj

            # scale of the shot generator should be the scale of channel
            # viewer multiplied by the ratio of window sizes
            scale_x, scale_y = self.fitsimage.get_scale_xy()
            c1_wd, c1_ht = self.fitsimage.get_window_size()
            c2_wd, c2_ht = self.shot_generator.get_window_size()

            scale_wd = float(c2_wd) / float(c1_wd)
            scale_ht = float(c2_ht) / float(c1_ht)
            scale = max(scale_wd, scale_ht)
            scale_x *= scale
            scale_y *= scale
            self.shot_generator.scale_to(scale_x, scale_y)

            self.fitsimage.copy_attributes(self.shot_generator,
                                           self.transfer_attrs)

            # snap image
            self.fv.error_wrap(self.shot_generator.save_rgb_image_as_file,
                               self.tmpname, format=format)

            c2.delete_all_objects(redraw=False)
            self.shot_generator._imgobj = None

        self.saved_type = format
        img = io_rgb.load_file(self.tmpname, logger=self.logger)

        # load the snapped image into the screenshot viewer
        self.scrnimage.set_image(img)

        image = self.fitsimage.get_image()
        name = image.get('name', 'NoName')
        name, _ext = os.path.splitext(name)
        wd, ht = img.get_size()
        save_name = name + '_{}x{}'.format(wd, ht) + '.' + format
        self.w.name.set_text(save_name)

    def _center_cb(self, w):
        """This function is called when the user clicks the 'Center' button.
        """
        self.scrnimage.center_image(no_reset=True)

    def _fit_cb(self, w):
        """This function is called when the user clicks the 'Fit' button.
        """
        self.scrnimage.zoom_fit(no_reset=True)

    def _full_cb(self, w):
        """This function is called when the user clicks the 'Full' button.
        """
        self.scrnimage.scale_to(1.0, 1.0, no_reset=True)

    def _clear_cb(self, w):
        """This function is called when the user clicks the 'Clear' button.
        """
        self.scrnimage.clear()

    def _save_cb(self, w):
        """This function is called when the user clicks the 'Save' button.
        We save the last taken shot to the folder and name specified.
        """
        format = self.saved_type
        if format is None:
            return self.fv.show_error("Please save an image first.")

        # create filename
        filename = self.w.name.get_text().strip()
        if len(filename) == 0:
            return self.fv.show_error("Please set a name for saving the file")
        self.save_name = filename

        if not filename.lower().endswith('.' + format):
            filename = filename + '.' + format

        # join to path
        path = self.w.folder.get_text().strip()
        if path == '':
            path = filename
        else:
            self.save_path = path
            path = os.path.join(path, filename)

        # copy last saved file
        self.fv.error_wrap(shutil.copyfile, self.tmpname, path)

    def _set_width_cb(self):
        """This function is called when the user enters a value into the
        'Width' entry field.  (this is only possible when 'Screen size' is
        unchecked)

        We calculate the height or aspect, depending on whether 'Lock aspect'
        is checked and update the shot generator viewer and UI.
        """
        wd, ht = self.get_wdht()
        aspect = self.get_aspect()
        if self._lock_aspect and aspect is not None:
            ht = int(round(wd * 1.0 / aspect))
            self.w.height.set_text(str(ht))
        else:
            _as = trcalc.calc_aspect_str(wd, ht)
            self.w.aspect.set_text(_as)

        self.shot_generator.configure_surface(wd, ht)
        self._sg_wd, self._sg_ht = wd, ht

    def _set_height_cb(self):
        """This function is called when the user enters a value into the
        'Height' entry field.  (this is only possible when 'Screen size' is
        unchecked)

        We calculate the width or aspect, depending on whether 'Lock aspect'
        is checked and update the shot generator viewer and UI.
        """
        wd, ht = self.get_wdht()
        aspect = self.get_aspect()
        if self._lock_aspect and aspect is not None:
            wd = int(round(ht * aspect))
            self.w.width.set_text(str(wd))
        else:
            _as = trcalc.calc_aspect_str(wd, ht)
            self.w.aspect.set_text(_as)

        self.shot_generator.configure_surface(wd, ht)
        self._sg_wd, self._sg_ht = wd, ht

    def _set_aspect_cb(self):
        """This function is called when the user enters a value into the
        'Aspect' entry field.  (this is only possible when 'Lock aspect' is
        checked)

        We calculate the width or aspect, depending on whether 'Lock aspect'
        is checked and update the shot generator viewer and UI.
        """
        wd, ht = self.get_wdht()
        aspect = self.get_aspect()
        if aspect is not None:
            wd, ht = self.calc_size_aspect(wd, ht, aspect)
            self.shot_generator.configure_surface(wd, ht)
            self._sg_wd, self._sg_ht = wd, ht
            self.w.width.set_text(str(wd))
            self.w.height.set_text(str(ht))

        self._sg_aspect = aspect

    def get_wdht(self):
        # get the width and height from the UI boxes, unless the screen
        # size is checked, in which case just return the channel viewers
        # width and height
        if self._screen_size:
            wd, ht = self.fitsimage.get_window_size()
        else:
            _wd = self.w.width.get_text().strip()
            if len(_wd) != 0:
                wd = int(_wd)
            _ht = self.w.height.get_text().strip()
            if len(_ht) != 0:
                ht = int(_ht)
        return wd, ht

    def get_aspect(self):
        # get the aspect ratio from the UI boxes if one is specified
        _as = self.w.aspect.get_text().strip()
        if len(_as) != 0:
            if ':' in _as:
                xa, ya = [float(v) for v in _as.split(':')]
                aspect = xa / ya
            else:
                aspect = float(_as)
            return aspect
        return None

    def check_and_adjust_dimensions(self):
        # check the dimensions of the shot generator and make sure they
        # match up with what is in the UI
        c2_wd, c2_ht = self.shot_generator.get_window_size()

        aspect = self.get_aspect()
        wd, ht = self.get_wdht()

        if self._lock_aspect and aspect is not None:
            wd, ht = self.calc_size_aspect(wd, ht, aspect)
            self.w.width.set_text(str(wd))
            self.w.height.set_text(str(ht))

        if c2_wd != wd or c2_ht != ht:
            self.shot_generator.configure_surface(wd, ht)

        self._sg_wd, self._sg_ht = wd, ht

    def _lock_aspect_cb(self, w, tf):
        """This function is called when the user clicks the 'Lock aspect'
        checkbox.  `tf` is True if checked, False otherwise.
        """
        self._lock_aspect = tf
        self.w.aspect.set_enabled(tf)
        if self._lock_aspect:
            self._set_aspect_cb()
        else:
            wd, ht = self.get_wdht()
            _as = trcalc.calc_aspect_str(wd, ht)
            self.w.aspect.set_text(_as)

    def calc_size_aspect(self, wd, ht, aspect):
        # adjust height or width to match the aspect ratio
        if aspect > 1.0:
            ht = int(round(wd * 1.0 / aspect))
        elif aspect < 1.0:
            wd = int(round(ht * aspect))
        else:
            wd = ht = min(wd, ht)
        return wd, ht

    def _screen_size_cb(self, w, tf):
        """This function is called when the user clicks the 'Screen size'
        checkbox.  `tf` is True if checked, False otherwise.
        """
        self._screen_size = tf
        self.w.width.set_enabled(not tf)
        self.w.height.set_enabled(not tf)
        self.w.lock_aspect.set_enabled(not tf)
        if self._screen_size:
            wd, ht = self.fitsimage.get_window_size()
            self._configure_cb(self.fitsimage, wd, ht)

    def _configure_cb(self, viewer, wd, ht):
        # called when the channel viewer changes size; set UI boxes with
        # the information about width, height and aspect ratio as necessary
        if not self.gui_up:
            return
        if self._screen_size:
            self.w.width.set_text(str(wd))
            self.w.height.set_text(str(ht))
            _as = trcalc.calc_aspect_str(wd, ht)
            self.w.aspect.set_text(_as)

    def __str__(self):
        return 'screenshot'

# END
