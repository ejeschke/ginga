from ginga.gtkw.ImageViewGtk import CanvasView, ScrolledView
from ginga.gtkw.ImageViewCanvasGtk import ImageViewCanvas
from ginga.gtkw import Widgets

class GingaViewerWidget(Widgets.WidgetBase):

    def __init__(self, viewer=None, width=600, height=600):
        super(GingaViewerWidget, self).__init__()

        if viewer is None:
            viewer = CanvasView(logger)
        self.logger = viewer.logger

        self.viewer = viewer
        self.widget = viewer.get_widget()

class GingaScrolledViewerWidget(Widgets.WidgetBase):

    def __init__(self, viewer=None, width=600, height=600):
        super(GingaScrolledViewerWidget, self).__init__()

        if viewer is None:
            viewer = CanvasView(logger)
        self.logger = viewer.logger

        self.viewer = viewer
        self.widget = ScrolledView(viewer)

    def scroll_bars(self, horizontal='on', vertical='on'):
        self.widget.scroll_bars(horizontal=horizontal,
                                vertical=vertical)

#END
