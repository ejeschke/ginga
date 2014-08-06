#
# ParamSet.py -- Groups of widgets holding parameters
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Widgets, Callback, Bunch


class ParamSet(Callback.Callbacks):
    def __init__(self, logger, params):
        super(ParamSet, self).__init__()
        
        self.logger = logger
        self.paramlst = []
        self.params = params
        self.widgets = {}

        for name in ('changed', ):
            self.enable_callback(name)
        
    def build_params(self, paramlst, orientation='vertical'):
        # construct a set of widgets for the parameters
        captions = []
        for param in paramlst:
            title = param.get('time', param.name)

            captions.append((title+':', 'label', param.name, 'entry'))

        w, b = Widgets.build_info(captions, orientation=orientation)

        # fill with default values and tool tips
        for param in paramlst:
            name = param.name

            # if we have a cached value for the parameter, use it
            if name in self.params:
                value = self.params[name]
                b[name].set_text(str(value))

            # otherwise initialize to the default value, if available
            elif 'default' in param:
                value = param.default
                b[name].set_text(str(value))
                self.params[name] = value

            if 'description' in param:
                b[name].set_tooltip(param.description)

            b[name].add_callback('activated', self._value_changed_cb)
            
        self.paramlst = paramlst
        self.widgets = b

        return w

    def _get_params(self):
        for param in self.paramlst:
            w = self.widgets[param.name]
            value = w.get_text()
            if 'type' in param:
                value = param.type(value)
            self.params[param.name] = value

    def sync_params(self):
        for param in self.paramlst:
            key = param.name
            w = self.widgets[key]
            if key in self.params:
                value = self.params[key]
                w.set_text(str(value))

    def get_params(self):
        self._get_params()
        return self.params
    
    def _value_changed_cb(self, w):
        self._get_params()
        self.make_callback('changed', self.params)
        

#END
