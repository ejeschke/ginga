#
# ParamSet.py -- Groups of widgets holding parameters
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Callback, Bunch
from ginga.gw import Widgets

class Param(Bunch.Bunch):
    pass

class ParamSet(Callback.Callbacks):
    def __init__(self, logger, obj):
        super(ParamSet, self).__init__()

        self.logger = logger
        self.paramlst = []
        self.obj = obj
        self.widgets = {}

        for name in ('changed', ):
            self.enable_callback(name)

    def get_widget_value(self, widget, param):
        if hasattr(widget, 'get_text'):
            return widget.get_text()
        elif hasattr(widget, 'get_index'):
            index = widget.get_index()
            value = param.valid[index]
            return value
        elif hasattr(widget, 'get_value'):
            return widget.get_value()
        elif hasattr(widget, 'get_state'):
            return widget.get_state()

    def set_widget_value(self, widget, param, value):
        if hasattr(widget, 'set_text'):
            widget.set_text(str(value))
        elif hasattr(widget, 'set_index'):
            idx = param.valid.index(value)
            widget.set_index(idx)
        elif hasattr(widget, 'set_value'):
            widget.set_value(value)
        elif hasattr(widget, 'set_state'):
            widget.set_state(value)

    def build_params(self, paramlst, orientation='vertical'):
        # construct a set of widgets for the parameters
        captions = []
        for param in paramlst:
            title = param.get('title', param.name)
            wtype = param.get('widget', None)
            ptype = param.get('type', str)
            if wtype is None:
                # set default widget type if none specified
                wtype = 'entry'
                if param.has_key('valid'):
                    wtype = 'combobox'

            captions.append((title+':', 'label', param.name, wtype))

        w, b = Widgets.build_info(captions, orientation=orientation)

        # fill with default values and tool tips
        for param in paramlst:
            name = param.name
            widget = b[name]
            valid = param.get('valid', None)

            if hasattr(widget, 'set_index') and valid is not None:
                # configure combobox
                for value in valid:
                    widget.append_text(str(value))

            elif hasattr(widget, 'set_limits') and param.has_key('incr'):
                # configure spinbox/slider
                widget.set_limits(param.min, param.max,
                                  incr_value=param.incr)

            wtype = param.get('widget', None)
            if wtype == 'spinfloat':
                widget.set_decimals(param.get('decimals', 4))

            # if we have a cached value for the parameter, use it
            try:
                value = getattr(self.obj, name)
                self.set_widget_value(widget, param, value)

            except (AttributeError, KeyError):
                # otherwise initialize to the default value, if available
                if 'default' in param:
                    value = param.default
                    self.set_widget_value(widget, param, value)
                    setattr(self.obj, name, value)

            if 'description' in param:
                widget.set_tooltip(param.description)

            if widget.has_callback('activated'):
                widget.add_callback('activated', self._value_changed_cb)
            elif widget.has_callback('value-changed'):
                widget.add_callback('value-changed', self._value_changed_cb)

        self.paramlst = paramlst
        self.widgets = b

        return w

    def _get_params(self):
        args, kwdargs = [], {}
        for param in self.paramlst:
            w = self.widgets[param.name]
            value = self.get_widget_value(w, param)
            if ('type' in param) and (value is not None):
                # hack
                if value == 'None':
                    value = None
                else:
                    value = param.type(value)
            setattr(self.obj, param.name, value)

            if param.has_key('argpos'):
                # TODO: ensure arg positioning is correct
                args.append(value)
            else:
                kwdargs[param.name] = value
        return args, kwdargs

    def get_params(self):
        return self._get_params()

    def params_to_widgets(self):
        for param in self.paramlst:
            name = param.name
            value = getattr(self.obj, name)
            self.set_widget_value(self.widgets[name], param,
                                  value)

    def sync_params(self):
        return self.params_to_widgets()

    def widgets_to_params(self):
        for param in self.paramlst:
            w = self.widgets[param.name]
            value = self.get_widget_value(w, param)
            if ('type' in param) and (value is not None):
                # hack
                if value == 'None':
                    value = None
                else:
                    value = param.type(value)
            setattr(self.obj, param.name, value)

    def _value_changed_cb(self, w, *args):
        self._get_params()
        self.make_callback('changed', self.obj)


#END
