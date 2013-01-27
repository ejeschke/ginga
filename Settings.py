#
# Settings.py -- Simple class to manage stateful user preferences.
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Thu Jan 24 15:34:18 HST 2013
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import pickle

import Callback
import Bunch

class Settings(object):
    def __init__(self, basefolder="/tmp", create_folders=True):
        self.folder = basefolder
        self.create = create_folders
        self.settings = Bunch.Bunch(caseless=True)

    def setDefaults(self, category, **kwdargs):
        for key, val in kwdargs.items():
            self.settings[category].setdefault(key, val)

    def getSettings(self, category):
        return self.settings[category]
    
    def createCategory(self, category):
        if not self.settings.has_key(category):
            self.settings[category] = Bunch.Bunch(caseless=True)
        return self.settings[category]

    def load(self, category, filename):
        category = category.lower()
        path = os.path.join(self.folder, category, filename)
        buf = None
        with open(path, 'r') as in_f:
            d = pickle.load(in_f)
        self.settings[category] = Bunch.Bunch(caseless=True)
        self.settings[category].update(d)
        #print "%s settings are: %s" % (category, str(self.settings[category]))
        return self.settings[category]
        
    def save(self, category, filename):
        category = category.lower()
        folder = os.path.join(self.folder, category)
        if (not os.path.exists(folder)) and self.create:
            os.mkdir(folder)
        path = os.path.join(folder, filename)
        d = {}
        d.update(self.settings[category])
        with open(path, 'w') as out_f:
            pickle.dump(d, out_f)

    def get_baseFolder(self):
        return self.folder


class Setting(Callback.Callbacks):

    def __init__(self, value=None, name=None, logger=None, check_fn=None):
        Callback.Callbacks.__init__(self)

        self.value = value
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
    
    def set(self, value):
        self.value = self.check_fn(value)
        self.make_callback('set', value)
        
    def get(self):
        return self.value
    
    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)
    

class SettingGroup(object):

    def __init__(self, logger=None):
        self.logger = logger

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
            return self.group[key].value
        else:
            d = { key: value }
            self.addSettings(**d)
            return self.group[key].value

    def addDefaults(self, **kwdargs):
        for key, value in kwdargs.items():
            self.setdefault(key, value)

    def get(self, key):
        return self.group[key].value
        
    def set(self, **kwdargs):
        for key, value in kwdargs.items():
            self.group[key].set(value)
        
    def __getitem__(self, key):
        return self.group[key].value
        
    def __setitem__(self, key, value):
        self.group[key].set(value)
        
#END
