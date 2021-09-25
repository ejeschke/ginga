#
# panzoom_base.py -- mode for scaling (zooming) and panning
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy as np

from ginga.misc import Bunch
from ginga.modes.mode_base import Mode


class PanZoomMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)
