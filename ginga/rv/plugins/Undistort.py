# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Undistort`` is a simple plugin to roughly "undistort" an image based on
it's SIP information a WCS.

**Plugin Type: Local**

``Undistort`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

Start the plugin on a channel.  Click "Undistort" to quickly correct the
distortion for the image in the channel.
"""
import os.path
from astropy.io import fits

from ginga import GingaPlugin, AstroImage
from ginga.misc import Future
from ginga.gw import Widgets
from ginga.util.undistort import quick_undistort_image

__all__ = ['Undistort']


class Undistort(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Undistort, self).__init__(fv, fitsimage)

        self.count = 1
        self.cache_dir = "/tmp"

    def build_gui(self, container):
        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        captions = (("Undistort", 'button', "_zzz", 'spacer'),
                    ("status", "llabel")
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        vtop.add_widget(w, stretch=0)

        b.undistort.add_callback('activated', self.undistort_cb)
        b.undistort.set_tooltip("Click to save channel image as undistorted image")
        b.status.set_text("")

        # stretch
        spacer = Widgets.Label('')
        vtop.add_widget(spacer, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vtop.add_widget(btns, stretch=0)

        container.add_widget(vtop, stretch=5)
        self.gui_up = True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def redo(self):
        pass

    def undistort(self, image, name=None, cache_dir=None):
        if image is None or image.wcs is None:
            self.fv.show_error("Undistort: null target image or WCS")
            return
        wcs_in = image.wcs.wcs
        data_in = image.get_data()

        # do undistortion
        data_out, wcs_out = quick_undistort_image(data_in, wcs_in)

        # TODO: use mask (probably as alpha mask)
        hdu = fits.PrimaryHDU(data_out)
        # add conversion wcs keywords
        hdu.header.update(wcs_out.to_header())
        if name is None:
            name = self.get_name(image.get('name'), cache_dir)

        # Write image to cache directory, if one is defined
        path = None
        if cache_dir is not None:
            path = os.path.join(cache_dir, name + '.fits')
            hdulst = fits.HDUList([hdu])
            hdulst.writeto(path)
            self.logger.info("wrote {}".format(path))

        img_out = AstroImage.AstroImage(logger=self.logger)
        img_out.load_hdu(hdu)
        img_out.set(name=name, path=path)

        return img_out

    def _undistort_cont(self, future):
        self.fv.gui_call(self.w.status.set_text, "")
        try:
            img_out = future.get_value()

        except Exception as e:
            self.fv.show_error("undistort error: {}".format(e))
            return

        if img_out is not None:
            self.fv.gui_do(self.channel.add_image, img_out)

    def undistort_cb(self, w):
        image = self.fitsimage.get_image()

        future = Future.Future()
        future.freeze(self.undistort, image, cache_dir=self.cache_dir)
        future.add_callback('resolved', self._undistort_cont)

        self.w.status.set_text("Working...")
        self.fv.nongui_do_future(future)

    def get_name(self, name_in, cache_dir):
        found = False
        while not found:
            name = name_in + '-undst-{}'.format(self.count)
            self.count += 1

            # Write image to cache directory, if one is defined
            path = None
            if cache_dir is None:
                return name

            path = os.path.join(cache_dir, name + '.fits')
            if not os.path.exists(path):
                return name

    def __str__(self):
        return 'undistort'
