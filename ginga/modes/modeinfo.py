from ginga.modes.cuts import CutsMode
from ginga.modes.contrast import ContrastMode
from ginga.modes.rotate import RotateMode
from ginga.modes.cmap import CMapMode
from ginga.modes.dist import DistMode
from ginga.modes.camera import CameraMode
from ginga.modes.naxis import NaxisMode
from ginga.modes.pan import PanMode
from ginga.modes.freepan import FreePanMode
#from ginga.modes.draw import DrawMode

available_modes = [CutsMode, ContrastMode, RotateMode, CMapMode,
                   DistMode, CameraMode, NaxisMode, PanMode, FreePanMode,
                   #DrawMode
                   ]


def add_mode(mode_class):
    available_modes.append(mode_class)
