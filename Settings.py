#
# Settings.py -- Simple class to manage stateful user preferences.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import pprint

import Callback
import Bunch


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
        if check_fn == None:
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

    def addSettings(self, **kwdargs):
        for key, value in kwdargs.items():
            self.group[key] = Setting(value=value, name=key,
                                      logger=self.logger)
            # TODO: add group change callback?
        
    def getSetting(self, key):
        return self.group[key]

    def shareSettings(self, other, keylist):
        for key in keylist:
            other.group[key] = self.group[key]

    def copySettings(self, other, keylist):
        for key in keylist:
            other.set(key, self.get(key))

    def setdefault(self, key, value):
        if self.group.has_key(key):
            return self.group[key].get(value)
        else:
            d = { key: value }
            self.addSettings(**d)
            return self.group[key].get(value)

    def addDefaults(self, **kwdargs):
        for key, value in kwdargs.items():
            self.setdefault(key, value)

    def setDefaults(self, **kwdargs):
        return self.addDefaults(**kwdargs)
    
    def get(self, *args):
        key = args[0]
        if len(args) == 1:
            return self.group[key].get()
        if len(args) == 2:
            return self.setdefault(key, args[1])

    def getDict(self):
        return dict([[name, self.group[name].value] for name in self.group.keys()])
            
    def setDict(self, d, callback=True):
        for key, value in d.items():
            if not self.group.has_key(key):
                self.setdefault(key, value)
            else:
                self.group[key].set(value, callback=callback)
        
    def set(self, **kwdargs):
        self.setDict(kwdargs)
        
    def load(self):
        with open(self.preffile, 'r') as in_f:
            buf = in_f.read()
            d = eval(buf)
            self.set(**d)
        
    def save(self):
        d = self.getDict()
        with open(self.preffile, 'w') as out_f:
            pprint.pprint(d, out_f)

    def __getitem__(self, key):
        return self.group[key].value
        
    def __setitem__(self, key, value):
        self.group[key].set(value)

    def has_key(self, key):
        return self.group.has_key(key)


class Preferences(object):

    def __init__(self, basefolder="/tmp", logger=None):
        self.folder = basefolder
        self.logger = logger
        self.settings = Bunch.Bunch(caseless=True)

    def setDefaults(self, category, **kwdargs):
        self.settings[category].addDefaults(**kwdargs)

    def getSettings(self, category):
        return self.settings[category]
    
    def getDict(self, category):
        return self.settings[category].getDict()
    
    def createCategory(self, category):
        if not self.settings.has_key(category):
            path = os.path.join(self.folder, category + ".prefs")
            self.settings[category] = SettingGroup(logger=self.logger,
                                                   name=category,
                                                   preffile=path)
        return self.settings[category]

    def get_baseFolder(self):
        return self.folder


        
#END
