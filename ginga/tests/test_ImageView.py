import logging

import numpy as np

from ginga import AstroImage
from ginga.pilw.ImageViewPil import CanvasView


class TestImageView:

    def setup_class(self):
        self.logger = logging.getLogger("TestImageView")
        self.viewer = CanvasView(logger=self.logger)
        self.data = np.identity(2000)
        self.image = AstroImage.AstroImage(logger=self.logger)
        self.image.set_data(self.data)

    def test_scale(self):
        viewer = self.viewer
        viewer.set_window_size(900, 1100)
        viewer.set_image(self.image)
        zoom = 0.0
        scale_x = scale_y = 1.0
        viewer.scale_to(scale_x, scale_y)
        zoomlevel = viewer.get_zoom()
        assert zoomlevel == zoom

    def test_centering(self):
        viewer = self.viewer
        viewer.set_window_size(900, 1100)
        viewer.set_image(self.image)
        viewer.center_image()
        ht, wd = self.data.shape[:2]
        ctr_x, ctr_y = wd / 2. - viewer.data_off, ht / 2. - viewer.data_off
        pan_x, pan_y = viewer.get_pan()
        assert np.isclose(pan_x, ctr_x) and np.isclose(pan_y, ctr_y)

    def test_pan(self):
        viewer = self.viewer
        viewer.set_window_size(900, 1100)
        viewer.set_image(self.image)
        viewer.set_pan(401.0, 501.0)
        pan_x, pan_y = viewer.get_pan()
        assert np.isclose(pan_x, 401.0) and np.isclose(pan_y, 501.0)

    def test_per_image_rgbmap_and_cuts(self):
        # A normimage overlay with its own rgbmap + cuts must be colormapped
        # and cut with those, independent of the viewer.  (Regression: the
        # NormImage constructor must forward rgbmap/cuts to NormImageP, and the
        # standard renderer's Cuts/RGBMap stages must honor them.)
        from ginga import RGBMap, cmap
        from ginga.canvas.CanvasObject import get_canvas_types
        get_canvas_types()

        viewer = CanvasView(logger=self.logger)
        # configure() (not just set_window_size()) so _imgwin_set is True and
        # redraw actually composites -- it's what every backend's
        # configure_window() hook and the programmatic examples call
        viewer.configure(120, 60)
        viewer.enable_autozoom('off')
        viewer.enable_autocuts('off')
        main = AstroImage.AstroImage(logger=self.logger)
        main.set_data(np.full((40, 80), 300.0, dtype=np.float32))
        viewer.set_image(main)
        viewer.cut_levels(0, 1000)
        viewer.scale_to(1.0, 1.0)

        canvas = viewer.get_canvas()
        NormImage = canvas.get_draw_class('normimage')
        rm = RGBMap.RGBMapper(self.logger)
        rm.set_cmap(cmap.get_cmap('rainbow'))
        ov = AstroImage.AstroImage(logger=self.logger)
        ov.set_data(np.full((15, 15), 900.0, dtype=np.float32))
        obj = NormImage(5, 5, ov, rgbmap=rm, cuts=(0, 1000))
        # the constructor must forward the per-image values
        assert obj.rgbmap is rm and obj.cuts == (0, 1000)

        canvas.add(obj)
        viewer.redraw_now(whence=0)
        arr = viewer.renderer.get_surface_as_array('RGB').astype(int)
        # the overlay's rainbow map yields colored (non-gray) pixels; under the
        # viewer's default gray map the same value would be gray
        colored = ~((arr[..., 0] == arr[..., 1]) & (arr[..., 1] == arr[..., 2]))
        assert int(colored.sum()) > 100

    def test_pan2(self):
        viewer = self.viewer
        viewer.set_window_size(400, 300)
        viewer.set_image(self.image)
        viewer.set_pan(401.0, 501.0)
        viewer.scale_to(8.0, 8.0)
        x1, y1, x2, y2 = viewer.get_data_rect()
        result = np.array([(x1, y1), (x2, y2)])
        expected = np.array([[376., 482.25], [426., 519.75]])
        assert np.all(np.isclose(expected, result))
