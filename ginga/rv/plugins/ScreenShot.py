#
# Screenshot.py -- Screenshot plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import shutil
import tempfile

from ginga import GingaPlugin
from ginga.RGBImage import RGBImage
from ginga.gw import Widgets, Viewers

class ScreenShot(GingaPlugin.LocalPlugin):
    """
    Screenshot
    ==========
    Capture PNG or JPEG images of the channel viewer image.

    Usage
    -----
    a) Select the RGB graphics type for the snap from the "Type" combo box.
    b) Press "Snap" when you have the channel image the way you want to capture it.

    A copy of the RGB image will be loaded into the screenshot viewer.
    You can pan and zoom within the screenshot viewer like a normal Ginga
    viewer to examine detail (e.g. see the magnified difference between
    JPEG and PNG formats).

    c) Repeat (a) and (b) until you have the image you want.
    d) Put a valid path for a new file into the "Folder" box.
    e) Put a valid name for a new file into the "Name" box.  There is no need to add the file extension; it will be added if needed.
    f) Press the "Save" button.  The file will be saved where you specified.

    Comments
    --------
    * PNG offers less artefacts for overlaid graphics, but files are larger than JPEG.
    * The "Center" button will center the snap image; "Fit" will set the zoom to fit it to the window; "Clear" will clear the image.
    * Press "1" in the screenshot viewer to zoom to 100% pixels.

    """
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
        zi.enable_autocenter('once')
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

        captions = (('Type:', 'label', 'grtype', 'combobox',
                    'Snap', 'button'),
                    ('Clear', 'button', 'Center', 'button', 'Fit', 'button',
                     'Full', 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w = b

        combobox = b.grtype
        for name in self.savetypes:
            combobox.append_text(name)
        index = self.savetypes.index(self.tosave_type)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_type(idx))
        combobox.set_tooltip("Set the format of the snap image")

        b.snap.set_tooltip("Click to grab a snapshot of this channel viewer image")
        b.snap.add_callback('activated', self.snap_cb)
        b.clear.set_tooltip("Clear the snap image")
        b.clear.add_callback('activated', self.clear_cb)
        b.center.set_tooltip("Center the snap image")
        b.center.add_callback('activated', self.center_cb)
        b.fit.set_tooltip("Fit snap image to window")
        b.fit.add_callback('activated', self.fit_cb)
        b.full.set_tooltip("View at 100% (1:1)")
        b.full.add_callback('activated', self.full_cb)

        vbox1.add_widget(w, stretch=0)

        fr = Widgets.Frame("Screenshot")
        fr.set_widget(vbox1)

        vpaned = Widgets.Splitter(orientation='vertical')
        vpaned.add_widget(fr)
        vpaned.add_widget(Widgets.Label(''))

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
        b.save.add_callback('activated', self.save_cb)

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

    def set_type(self, idx):
        self.tosave_type = self.savetypes[idx]
        return True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        pass

    def stop(self):
        self.saved_type = None

    def snap_cb(self, w):
        format = self.tosave_type
        # snap image
        self.fv.error_wrap(self.fitsimage.save_rgb_image_as_file,
                           self.tmpname, format=format)
        self.saved_type = format

        img = RGBImage(logger=self.logger)
        img.load_file(self.tmpname)

        self.scrnimage.set_image(img)

    def save_cb(self, w):
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

    def center_cb(self, w):
        self.scrnimage.center_image(no_reset=True)

    def fit_cb(self, w):
        self.scrnimage.zoom_fit(no_reset=True)

    def full_cb(self, w):
        self.scrnimage.scale_to(1.0, 1.0, no_reset=True)

    def clear_cb(self, w):
        self.scrnimage.clear()

    def __str__(self):
        return 'screenshot'

#END
