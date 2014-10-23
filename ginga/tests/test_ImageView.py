import unittest
import logging
import numpy

from ginga import AstroImage
from ginga.mockw.ImageViewCanvasMock import ImageViewCanvas

class TestError(Exception):
    pass

class TestImageView(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger("TestImageView")
        self.viewer = ImageViewCanvas(logger=self.logger)
        self.data = numpy.identity(2000)
        self.image = AstroImage.AstroImage(logger=self.logger)
        self.image.set_data(self.data)

    def test_scale(self):
        viewer = self.viewer
        viewer.set_window_size(900, 1100)
        viewer.set_image(self.image)
        zoom = 1.0
        scale_x = scale_y = 1.0 / abs(zoom)
        viewer.scale_to(scale_x, scale_y)
        zoomlevel = viewer.get_zoom()
        assert zoomlevel == zoom, \
               TestError("Zoom level has unexpected value (%f != %f)" % (
            zoomlevel, zoom))

    def test_pan(self):
        viewer = self.viewer
        viewer.set_window_size(900, 1100)
        viewer.set_image(self.image)
        ctr_x, ctr_y = viewer.get_center()
        viewer.set_pan(ctr_x, ctr_y)
        pan_x, pan_y = viewer.get_pan()
        assert ((pan_x == ctr_x) and (pan_y == ctr_y)), \
               TestError("Pan position is not at center (%f,%f != %f,%f)" % (
            pan_x, pan_y, ctr_x, ctr_y))

        ## off_x, off_y = viewer.canvas2offset(200, 200)
        ## print "200,200 absolute canvas2offset ->", off_x, off_y
        ## data_x, data_y = viewer.get_data_xy(200, 200)
        ## print "200,200 data xy ->", data_x, data_y

        ## win_x, win_y = viewer.offset2canvas(200, 200)
        ## print "200,200 relative offset2canvas ->", win_x, win_y
        ## win_x, win_y = viewer.get_canvas_xy(200, 200)
        ## print "200,200 canvas xy ->", win_x, win_y

        ## x1, y1, x2, y2 = viewer.get_datarect()
        ## print "getting canvas for %d,%d (%d,%d)" % (x1, y1, x2, y2)
        ## dst_x, dst_y = viewer.get_canvas_xy(x1, y2)
        ## print (x1, y2)
        ## print (dst_x, dst_y)
        
        
    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()

#END
