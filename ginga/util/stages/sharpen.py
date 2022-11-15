# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

## from PIL import Image, ImageFilter
from scipy.ndimage.filters import median_filter
import cv2

from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage, StageAction


class Sharpen(Stage):
    """
    The Sharpen stage will perform an unsharp mask on a 2D image.

    """

    _stagename = 'sharpen'

    def __init__(self):
        super().__init__()

        self._radius = 2
        self._strength = 1.0

    def build_gui(self, container):
        fr = Widgets.Frame("Sharpen")

        captions = (('Radius:', 'label', 'radius', 'entryset'),
                    ('Strength:', 'label', 'strength', 'entryset'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        b.radius.set_tooltip("Set the radius of the sharpening in pixels")
        b.radius.set_text(str(self._radius))
        b.radius.add_callback('activated', self.set_radius_cb)

        b.strength.set_tooltip("Set the strength of the sharpening")
        b.strength.set_text(str(self._strength))
        b.strength.add_callback('activated', self.set_strength_cb)

        self.w.update(b)
        fr.set_widget(w)

        container.set_widget(fr)

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, val):
        self._radius = val
        if self.gui_up:
            self.w.radius.set_text(str(self._radius))

    def _set_radius(self, radius):
        old_radius, self.radius = self._radius, radius
        self.pipeline.push(StageAction(self,
                                       dict(radius=old_radius),
                                       dict(radius=self._radius),
                                       descr="sharpen radius"))
        self.pipeline.run_from(self)

    @property
    def strength(self):
        return self._strength

    @strength.setter
    def strength(self, val):
        self._strength = val
        if self.gui_up:
            self.w.strength.set_text(str(self._strength))

    def _set_strength(self, strength):
        old_strength, self.strength = self._strength, strength
        self.pipeline.push(StageAction(self,
                                       dict(strength=old_strength),
                                       dict(strength=self._strength),
                                       descr="sharpen strength"))
        self.pipeline.run_from(self)

    def _get_state(self):
        return dict(radius=self._radius, strength=self._strength)

    def set_radius_cb(self, widget):
        radius = int(widget.get_text().strip())
        self._set_radius(radius)

    def set_strength_cb(self, widget):
        strength = float(widget.get_text().strip())
        self._set_strength(strength)

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

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.radius = d['radius']
        self.strength = d['strength']


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
