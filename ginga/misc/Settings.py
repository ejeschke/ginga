#
# Settings.py -- Simple class to manage stateful user preferences.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import ast

import numpy as np

from . import Callback
from . import Bunch

unset_value = ("^^UNSET^^")


class SettingError(Exception):
    pass


class Setting(Callback.Callbacks):

    def __init__(self, value=unset_value, name=None, logger=None,
                 check_fn=None):
        Callback.Callbacks.__init__(self)

        self.value = value
        self._unset = (value == unset_value)
        self.name = name
        self.logger = logger
        if check_fn is None:
            check_fn = self._check_none
        self.check_fn = check_fn

        # For callbacks
        for name in ('set', ):
            self.enable_callback(name)

    def _check_none(self, value):
        return value

    def set(self, value, callback=True):
        self.value = self.check_fn(value)
        if callback:
            self.make_callback('set', value)

    def get(self, *args):
        if self._unset:
            if len(args) == 0:
                raise KeyError("setting['%s'] value is not set!" % (
                    self.name))
            else:
                assert len(args) == 1, \
                    SettingError("Illegal parameter use to get(): %s" % (
                        str(args)))
                return args[0]
        return self.value

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)


class SettingGroup(object):

    def __init__(self, name=None, logger=None, preffile=None):
        self.name = name
        self.logger = logger
        self.preffile = preffile

        self.group = Bunch.Bunch()

    def add_settings(self, **kwdargs):
        for key, value in kwdargs.items():
            self.group[key] = Setting(value=value, name=key,
                                      logger=self.logger)
            # TODO: add group change callback?

    def get_setting(self, key):
        return self.group[key]

    def share_settings(self, other, keylist=None):
        if keylist is None:
            keylist = self.group.keys()
        for key in keylist:
            other.group[key] = self.group[key]

    def copy_settings(self, other, keylist=None):
        if keylist is None:
            keylist = self.group.keys()
        d = {}
        for key in keylist:
            d[key] = self.get(key)
        other.setDict(d)

    def setdefault(self, key, value):
        if key in self.group:
            return self.group[key].get(value)
        else:
            d = {key: value}
            self.add_settings(**d)
            return self.group[key].get(value)

    def add_defaults(self, **kwdargs):
        for key, value in kwdargs.items():
            self.setdefault(key, value)

    def set_defaults(self, **kwdargs):
        return self.add_defaults(**kwdargs)

    def get(self, *args):
        key = args[0]
        if len(args) == 1:
            return self.group[key].get()
        if len(args) == 2:
            return self.setdefault(key, args[1])

    def get_dict(self):
        return dict([[name, self.group[name].value]
                     for name in self.group.keys()])

    def set_dict(self, d, callback=True):
        for key, value in d.items():
            if key not in self.group:
                self.setdefault(key, value)
            else:
                self.group[key].set(value, callback=False)

        if callback:
            # make callbacks only after all items are set in the group
            for key, value in d.items():
                self.group[key].make_callback('set', value)

    def set(self, callback=True, **kwdargs):
        self.set_dict(kwdargs, callback=callback)

    def __getitem__(self, key):
        return self.group[key].value

    def __setitem__(self, key, value):
        self.group[key].set(value)

    def has_key(self, key):
        return key in self.group

    def load(self, onError='raise'):
        try:
            d = {}
            with open(self.preffile, 'r') as in_f:
                buf = in_f.read()
            for line in buf.split('\n'):
                line = line.strip()
                # skip comments and anything that doesn't look like an
                # assignment
                if line.startswith('#') or (not ('=' in line)):
                    continue
                else:
                    try:
                        i = line.index('=')
                        key = line[:i].strip()
                        val = ast.literal_eval(line[i + 1:].strip())
                        d[key] = val
                    except Exception as e:
                        # silently skip parse errors, for now
                        continue

            self.set_dict(d)
        except Exception as e:
            errmsg = "Error opening settings file (%s): %s" % (
                self.preffile, str(e))
            if onError == 'silent':
                pass
            elif onError == 'warn':
                self.logger.warning(errmsg)
            else:
                raise SettingError(errmsg)

    def _check(self, d):
        if isinstance(d, dict):
            for key, value in d.items():
                d[key] = self._check(value)
            return d
        try:
            if np.isnan(d):
                return 0.0
            elif np.isinf(d):
                return 0.0
        except Exception:
            pass
        return d

    def save(self):
        d = self.get_dict()
        # sanitize data -- hard to parse NaN or Inf
        self._check(d)
        try:
            # sort keys for easy reading/editing
            keys = list(d.keys())
            keys.sort()
            with open(self.preffile, 'w') as out_f:
                for key in keys:
                    out_f.write("%s = %s\n" % (key, repr(d[key])))

        except Exception as e:
            errmsg = "Error opening settings file (%s): %s" % (
                self.preffile, str(e))
            self.logger.error(errmsg)

    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    addSettings = add_settings
    getSetting = get_setting
    shareSettings = share_settings
    copySettings = copy_settings
    addDefaults = add_defaults
    setDefaults = set_defaults
    getDict = get_dict
    setDict = set_dict


class Preferences(object):

    def __init__(self, basefolder=None, logger=None):
        self.folder = basefolder
        self.logger = logger
        self.settings = Bunch.Bunch(caseless=True)

    def set_defaults(self, category, **kwdargs):
        self.settings[category].add_defaults(**kwdargs)

    def get_settings(self, category):
        return self.settings[category]

    def remove_settings(self, category):
        del self.settings[category]

    def get_dict_category(self, category):
        return self.settings[category].get_dict()

    def create_category(self, category):
        if category not in self.settings:
            suffix = '.cfg'
            path = os.path.join(self.folder, category + suffix)
            self.settings[category] = SettingGroup(logger=self.logger,
                                                   name=category,
                                                   preffile=path)
        return self.settings[category]

    def get_base_folder(self):
        return self.folder

    def get_dict(self):
        return dict([[name, self.settings[name].get_dict()] for name in
                     self.settings.keys()])

    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    setDefaults = set_defaults
    getSettings = get_settings
    createCategory = create_category
    get_baseFolder = get_base_folder
    getDict = get_dict


#END
