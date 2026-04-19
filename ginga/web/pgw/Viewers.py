# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.web.pgw.ImageViewPg import CanvasView
from ginga.web.pgw import Widgets


class GingaViewerWidget(Widgets.Image):
    """
    This class implements the server-side backend of the surface for a
    web-based Ginga viewer.  It uses a web socket to connect to an HTML5
    canvas with javascript callbacks in a web browser on the client.

    The viewer is created separately on the backend and connects to this
    surface via the set_viewer() method.
    """

    def __init__(self, viewer=None, width=600, height=600):
        super().__init__(interactive=True, use_animation_frame=True)

        self.resize(width, height)

        if viewer is None:
            viewer = CanvasView()
        self.logger = viewer.logger

        self.set_viewer(viewer)

    def set_viewer(self, viewer):
        self.logger.debug("set_viewer called")
        self.viewer = viewer

        self.viewer.set_widget(self)

    def get_viewer(self):
        return self.viewer


class GingaScrolledViewerWidget(GingaViewerWidget):

    def scroll_bars(self, horizontal='on', vertical='on'):
        # until implemented
        pass

    def get_scroll_bars_status(self):
        return dict(horizontal='off', vertical='off')


class ScrolledView(GingaScrolledViewerWidget):
    pass
