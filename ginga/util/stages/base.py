#
# stage.py -- Classes for pipeline stages
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch

#__all__ = ['Pipeline']


class StageError(Exception):
    pass


class Stage(object):
    """Class to handle a pipeline stage."""

    _stagename = 'generic'

    def __init__(self):
        super(Stage, self).__init__()

        # default name, until user changes it
        self.name = str(self)
        # for holding widgets
        self.w = Bunch.Bunch()
        self._bypass = False
        # these get assigned by the owning pipeline
        self.pipeline = None
        self.logger = None
        self.result = None
        self.gui_up = False

    def build_gui(self, container):
        """subclass can override this to build some kind of GUI."""
        pass

    def start(self):
        """subclass can override this to do any necessary setup."""
        pass

    def stop(self):
        """subclass can override this to do any necessary teardown."""
        pass

    def pause(self):
        """subclass can override this to do any necessary teardown."""
        pass

    def resume(self):
        """subclass can override this to do any necessary teardown."""
        pass

    def invalidate(self):
        """subclass can override this to do any necessary invalidation."""
        pass

    def bypass(self, tf):
        self._bypass = tf

    def verify_2d(self, data):
        if data is not None and len(data.shape) < 2:
            raise StageError("Expecting a 2D or greater array in final stage")

    def export_as_dict(self):
        d = dict(name=self.name, type=self._stagename, bypass=self._bypass)
        return d

    def import_from_dict(self, d):
        self.name = d['name']
        self._bypass = d['bypass']

    def __str__(self):
        return self._stagename
