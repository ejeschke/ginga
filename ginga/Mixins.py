#
# Mixins.py -- Mixin classes for FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga.misc.Callback import Callbacks

class UIMixin(object):

    def __init__(self):
        self.ui_active = False

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                    ):
            self.enable_callback(name)

    def ui_isActive(self):
        return self.ui_active

    def ui_setActive(self, tf):
        # if tf:
        #     print "Layer %s set to active" % str(self)
        #     traceback.print_stack()
        self.ui_active = tf

    ## def make_callback(self, name, *args, **kwdargs):
    ##     if hasattr(self, 'objects'):
    ##         # Invoke callbacks on all our layers that have the UI mixin
    ##         for obj in self.objects:
    ##             if isinstance(obj, UIMixin) and obj.ui_isActive():
    ##                 obj.make_callback(name, *args, **kwdargs)

    ##     return super(UIMixin, self).make_callback(name, *args, **kwdargs)

    def make_ui_callback(self, name, *args, **kwdargs):
        """Invoke callbacks on all objects (i.e. layers) from the top to
        the bottom, returning when the first one returns True.  If none
        returns True, then make the callback on our 'native' layer.
        """
        #print("(in %s)make callback %s" % (self.name, name))
        if hasattr(self, 'objects'):
            # Invoke callbacks on all our layers that have the UI mixin
            num = len(self.objects) - 1
            #print("make callback %s 2: num=%d" % (name, num))
            while num >= 0:
                obj = self.objects[num]
                #print("make callback %s 3: obj=%s" % (name, obj.name))
                if isinstance(obj, UIMixin) and obj.ui_isActive():
                #if hasattr(obj, 'ui_isActive') and obj.ui_isActive():
                    #print(("(sub)making callback '%s' on %s" % (name, obj.name)))
                    res = obj.make_ui_callback(name, *args, **kwdargs)
                    #print(("(sub)result was %s" % (res)))
                    if res:
                        return res
                num -= 1

        if self.ui_active:
            #print(("making callback '%s' on %s" % (name, self.name)))
            return super(UIMixin, self).make_callback(name, *args, **kwdargs)

    def make_callback_children(self, name, *args, **kwdargs):
        """Invoke callbacks on all objects (i.e. layers) from the top to
        the bottom, returning when the first one returns True.  If none
        returns True, then make the callback on our 'native' layer.
        """
        #print("(in %s)make callback %s" % (self.name, name))
        if hasattr(self, 'objects'):
            # Invoke callbacks on all our layers that have the UI mixin
            num = len(self.objects) - 1
            #print("make callback %s 2: num=%d" % (name, num))
            while num >= 0:
                obj = self.objects[num]
                #print("make callback %s 3: obj=%s" % (name, obj.name))
                #print(("(sub)making callback '%s' on %s" % (name, obj.name)))
                if isinstance(obj, Callbacks):
                    res = obj.make_callback(name, *args, **kwdargs)
                    #print(("(sub)result was %s" % (res)))
                    ## if res:
                    ##     return res
                num -= 1

        #print(("making callback '%s' on %s" % (name, self.name)))
        return super(UIMixin, self).make_callback(name, *args, **kwdargs)


# END
