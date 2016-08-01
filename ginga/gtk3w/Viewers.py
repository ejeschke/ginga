from ginga.gtk3w.ImageViewGtk import CanvasView
from ginga.gtk3w.ImageViewCanvasGtk import ImageViewCanvas
from ginga.gtk3w import Widgets

class GingaViewerWidget(Widgets.WidgetBase):

    def __init__(self, viewer=None, width=600, height=600):
        super(GingaViewerWidget, self).__init__()

        if viewer is None:
            viewer = CanvasView(logger)
        self.logger = viewer.logger

        self.viewer = viewer
        self.widget = viewer.get_widget()

#END
