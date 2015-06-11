
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from ginga.mplw.ImageViewCanvasMpl import ImageViewCanvas
from ginga.misc import log
from ginga.AstroImage import AstroImage
from ginga import cmap
# add matplotlib colormaps to ginga's own set
cmap.add_matplotlib_cmaps()

## from IPython.display import Image
## from io import BytesIO


class CustomMplViewer(ImageViewCanvas):

    def get_nb_image(self):
        return Image(data=bytes(self.get_rgb_image_as_bytes(format='png')),
                     format='png', embed=True)

    def load(self, filepath):
        image = AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.set_image(image)

    def show(self):
        self.figure.show()

    def add_canvas(self, tag=None):
        # add a canvas to the view
        DrawingCanvas = self.getDrawClass('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.ui_setActive(True)
        canvas.setSurface(self)
        # add the canvas to the view.
        self.add(canvas, tag=tag)
        return canvas


def get_viewer():
    # Set to True to get diagnostic logging output
    use_logger = False
    logger = log.get_logger(null=not use_logger, log_stderr=True)

    # create a regular matplotlib figure
    fig = plt.figure()

    # create a ginga object, initialize some defaults and
    # tell it about the figure
    viewer = CustomMplViewer(logger)
    viewer.enable_autocuts('on')
    viewer.set_autocut_params('zscale')
    viewer.set_figure(fig)

    # enable all interactive ginga features
    viewer.get_bindings().enable_all(True)

    return viewer
