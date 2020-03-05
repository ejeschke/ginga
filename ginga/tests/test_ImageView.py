import logging

import numpy as np

from ginga import AstroImage
from ginga.mockw.ImageViewMock import CanvasView


class TestImageView(object):

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

    def test_pan2(self):
        viewer = self.viewer
        viewer.set_window_size(400, 300)
        viewer.set_image(self.image)
        viewer.set_pan(401.0, 501.0)
        viewer.scale_to(8.0, 8.0)
        x1, y1, x2, y2 = viewer.get_datarect()
        result = np.array([(x1, y1), (x2, y2)])
        expected = np.array([[376., 482.25], [426., 519.75]])
        assert np.all(np.isclose(expected, result))
