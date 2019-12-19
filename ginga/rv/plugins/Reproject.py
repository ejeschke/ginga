# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Reproject`` is a simple plugin to reproject an image from one WCS to
another.

**Plugin Type: Local**

``Reproject`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

Start the plugin on a channel.  Load the image which has the WCS that you
want to use for the reprojection into the channel.  Click "Set WCS" to save
the WCS; you will see the image copied into the plugin viewer and the
message "WCS set" will briefly appear there.

Now load any image that you want to reproject into the channel.  Click
"Reproject" to reproject the image using the saved image and it's header/WCS
to do so.  The reprojected image will appear in the channel as a separate
image.  You can keep loading images and reprojecting them.  If you want to
do a different reprojection, simply repeat the "Set WCS", "Reproject"
sequence at any time.

The parameters for the reprojection can be set in the GUI controls.
"""
import os.path
import numpy as np
from astropy.io import fits
import reproject

from ginga import GingaPlugin, AstroImage
from ginga.gw import Widgets, Viewers

__all__ = ['Reproject']


_choose = {'adaptive': dict(order=['nearest-neighbor', 'bilinear'],
                            method=reproject.reproject_adaptive),
           'interp': dict(order=['nearest-neighbor', 'bilinear',
                                 'biquadratic', 'bicubic'],
                          method=reproject.reproject_interp),
           'exact': dict(order=['n/a'],
                         method=reproject.reproject_exact),
           }


class Reproject(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Reproject, self).__init__(fv, fitsimage)

        self._wd = 400
        self._ht = 300
        _sz = max(self._wd, self._ht)
        # hack to set a reasonable starting position for the splitter
        self._split_sizes = [_sz, _sz]

        self.count = 1
        self.cache_dir = "/tmp"
        self.out_wcs = None
        self._proj_types = list(_choose.keys())
        self._proj_types.sort()
        self._proj_type = self._proj_types[0]

    def build_gui(self, container):
        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container)
        # Uncomment to debug; passing parent logger generates too
        # much noise in the main logger
        zi = Viewers.CanvasView(logger=self.logger)
        zi.set_desired_size(self._wd, self._ht)
        zi.enable_autozoom('override')
        zi.enable_autocuts('override')
        zi.set_bg(0.4, 0.4, 0.4)
        zi.show_pan_mark(True)
        # for debugging
        zi.set_name('reproject-image')
        self.rpt_image = zi

        bd = zi.get_bindings()
        bd.enable_all(True)

        iw = Viewers.GingaViewerWidget(zi)
        iw.resize(self._wd, self._ht)
        paned = Widgets.Splitter(orientation=orientation)
        paned.add_widget(iw)
        self.w.splitter = paned

        vbox2 = Widgets.VBox()
        captions = (("Reproject", 'button', "Set WCS", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        b.reproject.add_callback('activated', self.reproject_cb)
        b.reproject.set_tooltip("Click to save channel image as reprojection WCS")
        b.set_wcs.add_callback('activated', self.set_wcs_cb)
        b.set_wcs.set_tooltip("Click to reproject channel image using saved WCS")

        captions = (("Reproject type", 'combobox'),
                    ("Order", 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        cb = b.reproject_type
        for name in self._proj_types:
            cb.insert_alpha(name)
        cb.set_tooltip("Set type of reprojection")
        cb.add_callback('activated', self.set_reprojection_cb)
        idx = self._proj_types.index(self._proj_type)
        cb.set_index(idx)

        self._adjust_orders()

        # stretch
        spacer = Widgets.Label('')
        vbox2.add_widget(spacer, stretch=1)

        box.add_widget(vbox2, stretch=1)

        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        vtop.add_widget(paned, stretch=5)

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

    def stop(self):
        self._split_sizes = self.w.splitter.get_sizes()

    def redo(self):
        pass

    def reproject(self, image, name=None, shape=None, cache_dir=None):
        if image is None or image.wcs is None:
            self.fv.show_error("Reproject: null target image or WCS")
            return
        wcs_in = image.wcs.wcs
        data_in = image.get_data()
        if shape is None:
            shape = image.shape

        proj_out = self.wcs_out

        method = _choose[self._proj_type]['method']

        kwargs = dict(return_footprint=True, shape_out=shape)
        order = self.w.order.get_text()
        if order != 'n/a':
            kwargs['order'] = order

        # do reprojection
        try:
            data_out, mask = method((data_in, wcs_in), proj_out,
                                    **kwargs)

        except Exception as e:
            self.fv.show_error("reproject error: {}".format(e))
            return None

        # TODO: use mask (probably as alpha mask)
        hdu = fits.PrimaryHDU(data_out)
        if name is None:
            name = self.get_name(image.get('name'), cache_dir)

        # Write image to cache directory, if one is defined
        path = None
        if cache_dir is not None:
            path = os.path.join(cache_dir, name + '.fits')
            hdulst = fits.HDUList([hdu])
            hdulst.writeto(path)
            self.logger.info("wrote {}".format(path))

        # TODO: decent header with WCS
        img_out = AstroImage.AstroImage(logger=self.logger)
        img_out.load_hdu(hdu)
        img_out.set(name=name, path=path)

        return img_out

    def set_wcs_cb(self, w):
        image = self.fitsimage.get_image()
        if image is None or image.wcs is None:
            return

        self.rpt_image.set_image(image)
        #self.wcs_out = image.wcs.wcs
        header = image.get_header()
        self.wcs_out = fits.Header(header)
        self.rpt_image.onscreen_message("WCS set", delay=1.0)

    def reproject_cb(self, w):
        image = self.fitsimage.get_image()
        img_out = self.reproject(image, cache_dir=self.cache_dir)

        if img_out is not None:
            self.channel.add_image(img_out)

    def get_name(self, name_in, cache_dir):
        found = False
        while not found:
            name = name_in + '-rpjt-{}'.format(self.count)
            self.count += 1

            # Write image to cache directory, if one is defined
            path = None
            if cache_dir is None:
                return name

            path = os.path.join(cache_dir, name + '.fits')
            if not os.path.exists(path):
                return name

    def set_reprojection_cb(self, w, idx):
        self._proj_type = w.get_text()
        self._adjust_orders()

    def _adjust_orders(self):
        order = _choose[self._proj_type]['order']
        self.w.order.clear()
        for name in order:
            self.w.order.insert_alpha(name)

    def __str__(self):
        return 'reproject'
