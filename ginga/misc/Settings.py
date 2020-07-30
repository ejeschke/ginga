#
# Settings.py -- Simple class to manage stateful user preferences.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import re
import ast

import numpy as np

from . import Callback
from . import Bunch

unset_value = "^^UNSET^^"
regex_assign = re.compile(r'^([a-zA-Z_]\w*)\s*=\s*(\S.*)$')
regex_array = re.compile(r'^\s*array\((\[.*\])\s*(,\s*dtype=(.+)\s*)?\)\s*$',
                         flags=re.DOTALL)


class SettingError(Exception):
    pass


class Setting(Callback.Callbacks):

    def __init__(self, value=unset_value, name=None, logger=None,
                 check_fn=None):
        Callback.Callbacks.__init__(self)

        self.value = value
        self._unset = np.isscalar(value) and value == unset_value
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
                if len(args) != 1:
                    raise SettingError("Illegal parameter use to get(): %s" % (
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

        # TODO: add group change callback?
        self.group = Bunch.Bunch()
        self._group_b = Bunch.Bunch()

    def add_settings(self, **kwdargs):
        for key, value in kwdargs.items():
            if key not in self.group:
                setting = Setting(value=value, name=key,
                                  logger=self.logger)
                self._mk_add_callback(key, setting)
                self.group[key] = setting
            # add to backup group
            if key not in self._group_b:
                self._group_b[key] = setting

    def get_setting(self, key):
        return self.group[key]

    def keys(self):
        return self.group.keys()

    def _mk_add_callback(self, key, setting):
        setting._add_callback = setting.add_callback

        def _add_callback(*args, **kwargs):
            self.group[key]._add_callback(*args, **kwargs)
            self._group_b[key]._add_callback(*args, **kwargs)

        setting.add_callback = _add_callback

    def share_settings(self, other, keylist=None, include_callbacks=True,
                       callback=True):
        """Sharing settings with `other`
        """
        if keylist is None:
            keylist = self.group.keys()
        if include_callbacks:
            for key in keylist:
                oset, mset = other.group[key], self.group[key]
                other.group[key] = mset
                oset.merge_callbacks_to(mset)
        if callback:
            # make callbacks only after all items are set in the group
            # TODO: only make callbacks for values that changed?
            for key in keylist:
                other.group[key].make_callback('set', other.group[key].value)

    def unshare_settings(self, keylist=None, callback=True):
        if keylist is None:
            keylist = self._group_b.keys()
        for key in keylist:
            # copy value from current setting, while restoring old setting
            if self.group[key] is not self._group_b[key]:
                value = self.group[key].value
                self.group[key] = self._group_b[key]
                self.group[key].set(value, callback=False)
        if callback:
            # make callbacks only after all items are set in the group
            # TODO: only make callbacks for values that changed?
            for key in keylist:
                self.group[key].make_callback('set', self.group[key].value)

    def copy_settings(self, other, keylist=None, include_callbacks=False,
                      callback=True):
        if keylist is None:
            keylist = self.group.keys()
        d = {key: self.get(key) for key in keylist}

        if include_callbacks:
            for key in keylist:
                oset, mset = other.group[key], self.group[key]
                mset.merge_callbacks_to(oset)

        other.set_dict(d, callback=callback)

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
        else:
            if key in self.group:
                return self.group[key].get(*args[1:])
            if len(args) > 2:
                raise SettingError("Illegal parameter use to get(): %s" % (
                    str(args)))
            return args[1]

    def get_dict(self, keylist=None):
        if keylist is None:
            keylist = self.group.keys()
        return dict([[name, self.group[name].value]
                     for name in keylist])

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

    # TODO: Should deprecate this and encourage __contains__ like Python dict
    def has_key(self, key):
        return key in self.group

    def __contains__(self, key):
        return key in self.group

    def clear_callbacks(self, keylist=None):
        if keylist is None:
            keylist = self.group.keys()

        for key in keylist:
            self.group[key].clear_callback('set')

    def load(self, onError='raise', buf=None):
        try:
            if buf is None:
                with open(self.preffile, 'r') as in_f:
                    buf = in_f.read()
            d = dict(list(eval_assignments(make_assignments(strip_comments(
                     buf.split('\n'))))))
            self.set_dict(d)

        except Exception as e:
            errmsg = "Error loading settings file (%s): %s" % (
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

    def _save(self, out_f, keys, d):
        for key in keys:
            val_s = repr(d[key])
            out_f.write("%s = %s\n" % (key, val_s))

    def save(self, keylist=None, output=None):
        d = self.get_dict(keylist=keylist)
        # sanitize data -- hard to parse NaN or Inf
        self._check(d)
        try:
            # sort keys for easy reading/editing
            keys = list(d.keys())
            keys.sort()

            if output is None:
                output = self.preffile
            if isinstance(output, str):
                with open(output, 'w') as out_f:
                    self._save(out_f, keys, d)
            else:
                self._save(output, keys, d)

        except Exception as e:
            errmsg = "Error writing settings output: %s" % (str(e))
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


def strip_comments(lines):
    """Strips all blank lines and comments from `lines`.

    Parameters
    ----------
    lines : iterable of str
        The input file, stripped into lines

    Returns
    -------
    results : iterable of (int, str)
        An iterable containing tuples of (line number, text)
    """
    for line_no, line in enumerate(lines):
        line = line.strip()
        if len(line) == 0 or line.startswith('#'):
            continue
        yield (line_no, line)


def make_assignments(results):
    """Makes line_no, kwd, value string triples.

    Parameters
    ----------
    results: iterable of (int, str)
        Output of `strip_comments()`

    Returns
    -------
    results: iterable of (int, str, str)
        An iterable containing tuples of (line_number, kwd, val_str)
    """
    building = False
    kwd, vals, n = None, [], 0
    for line_no, line in results:
        match = regex_assign.match(line)
        if match:
            if building:
                yield n, kwd, ' '.join(vals)

            building = True
            n = line_no
            kwd, val = match.groups()
            vals = [val]
        else:
            if building:
                vals.append(line)
            else:
                raise Exception("Unexpected syntax on line {}: {}".format(line_no, line))

    if len(vals) > 0:
        yield n, kwd, ' '.join(vals)


def eval_assignments(results):
    """Makes kwd, value pairs.

    Parameters
    ----------
    results: iterable of (int, str, str)
        Output of `make_assignments()`

    Returns
    -------
    results: iterable of (str, val)
        An iterable containing tuples of (kwd, val)
    """
    for line_no, kwd, val_s in results:
        match = regex_array.match(val_s)
        if match:
            data, _x, dtype = match.groups()
            # special case for parsing numpy arrays
            val = np.asarray(ast.literal_eval(data), dtype=dtype)
        else:
            val = ast.literal_eval(val_s)

        yield kwd, val
