#
# Mixins.py -- Mixin classes for FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga.misc.Callback import Callbacks


class UIMixin(object):

    def __init__(self):
        self.ui_active = False
        self.ui_viewer = set([])

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'cursor-changed'):
            self.enable_callback(name)

    def ui_is_active(self):
        return self.ui_active

    def ui_set_active(self, tf, viewer=None):
        self.ui_active = tf
        if viewer is not None:
            if tf:
                self.ui_viewer.add(viewer)
            else:
                if viewer in self.ui_viewer:
                    self.ui_viewer.remove(viewer)

    def make_ui_callback(self, name, *args, **kwargs):
        """Invoke callbacks on all objects (i.e. layers) from the top to
        the bottom, returning when the first one returns True.  If none
        returns True, then make the callback on our 'native' layer.
        """
        if hasattr(self, 'objects'):
            # Invoke callbacks on all our layers that have the UI mixin
            num = len(self.objects) - 1
            while num >= 0:
                obj = self.objects[num]
                if isinstance(obj, UIMixin) and obj.ui_is_active():
                    res = obj.make_ui_callback(name, *args, **kwargs)
                    if res:
                        return res
                num -= 1

        if self.ui_active:
            return super(UIMixin, self).make_callback(name, *args, **kwargs)

    def make_ui_callback_viewer(self, viewer, name, *args, **kwargs):
        """Invoke callbacks on all objects (i.e. layers) from the top to
        the bottom, returning when the first one returns True.  If none
        returns True, then make the callback on our 'native' layer.
        """
        if len(self.ui_viewer) == 0 or viewer in self.ui_viewer:
            if hasattr(self, 'objects'):
                # Invoke callbacks on all our layers that have the UI mixin
                num = len(self.objects) - 1
                while num >= 0:
                    obj = self.objects[num]
                    if isinstance(obj, UIMixin) and obj.ui_is_active():
                        res = obj.make_ui_callback_viewer(viewer, name,
                                                          *args, **kwargs)
                        if res:
                            return res
                    num -= 1

            if self.ui_active:
                return super(UIMixin, self).make_callback(name, *args, **kwargs)

    def make_callback_children(self, name, *args, **kwargs):
        """Invoke callbacks on all objects (i.e. layers) from the top to
        the bottom, returning when the first one returns True.  If none
        returns True, then make the callback on our 'native' layer.
        """
        if hasattr(self, 'objects'):
            # Invoke callbacks on all our layers that have the UI mixin
            num = len(self.objects) - 1
            while num >= 0:
                obj = self.objects[num]
                if isinstance(obj, Callbacks):
                    obj.make_callback(name, *args, **kwargs)
                num -= 1

        return super(UIMixin, self).make_callback(name, *args, **kwargs)

    ### NON-PEP8 EQUIVALENTS -- TO BE DEPRECATED ###
    ui_isActive = ui_is_active
    ui_setActive = ui_set_active

# END
