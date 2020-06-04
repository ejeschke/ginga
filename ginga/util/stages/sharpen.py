# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

## from PIL import Image, ImageFilter
from scipy.ndimage.filters import median_filter
import cv2

from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage


class Sharpen(Stage):
    """
    The Sharpen stage will perform an unsharp mask on a 2D image.

    """

    _stagename = 'sharpen'

    def __init__(self):
        super(Sharpen, self).__init__()

        self.radius = 2
        self.strength = 1.0

    def build_gui(self, container):
        fr = Widgets.Frame("Sharpen")

        captions = (('Radius:', 'label', 'radius', 'entryset'),
                    ('Strength:', 'label', 'strength', 'entryset'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        b.radius.set_tooltip("Set the radius of the sharpening in pixels")
        b.radius.set_text(str(self.radius))
        b.radius.add_callback('activated', self.set_radius_cb)

        b.strength.set_tooltip("Set the strength of the sharpening")
        b.strength.set_text(str(self.strength))
        b.strength.add_callback('activated', self.set_strength_cb)

        self.w.update(b)
        fr.set_widget(w)

        container.set_widget(fr)

    def set_radius_cb(self, widget):
        self.radius = int(widget.get_text().strip())
        self.pipeline.run_from(self)

    def set_strength_cb(self, widget):
        self.strength = float(widget.get_text().strip())
        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass:
            self.pipeline.send(res_np=data)
            return

        ## img = Image.fromarray(data)

        ## pct = int(round(self.strength * 100))
        ## sharp_img = img.filter(ImageFilter.UnsharpMask(radius=self.radius,
        ##                                                percent=pct))

        ## res_np = np.array(sharp_img, dtype=data.dtype)

        res_np = unsharpen(data, self.radius, self.strength)

        self.pipeline.send(res_np=res_np)


def unsharp(imarr, sigma, strength, minmax=None):
    """
    Credit: Unsharp masking with Python and OpenCV
    https://www.idtools.com.au/unsharp-masking-python-opencv/
    """
    if minmax is None:
        minmax = trcalc.get_minmax_dtype(imarr.dtype)

    # Median filtering
    image_mf = median_filter(imarr, sigma)

    # Calculate the Laplacian
    lap = cv2.Laplacian(image_mf, cv2.CV_64F)

    # Calculate the sharpened image
    sharp = (imarr - strength * lap).clip(minmax[0], minmax[1])
    return sharp


def unsharpen(imarr, sigma, strength):
    res = np.zeros_like(imarr)
    if len(imarr.shape) < 3:
        # monochrome image
        return unsharp(imarr, sigma, strength)

    # RGB image
    for i in range(imarr.shape[2]):
        res[:, :, i] = unsharp(imarr[:, :, i], sigma, strength)

    return res
