#
# json.py -- augment JSON parsing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import json

from ginga.misc import Bunch


class BunchEncoder(json.JSONEncoder):
    """Custom encoder to serialize Ginga's Bunch.Bunch class.

    Usage
    -----
      json.dumps(objs, indent=2, cls=BunchEncoder)

    """
    def default(self, obj):
        if isinstance(obj, Bunch.Bunch):
            d = dict(__bunch__=True)
            d.update(obj)
            return d
        return json.JSONEncoder.default(self, obj)


def as_bunch(dct):
    """Custom decoder to deserialize Ginga's Bunch.Bunch class.

    Usage
    -----
      json.loads(buf, )

    """
    if '__bunch__' in dct:
        d = dct.copy()
        del d['__bunch__']
        return Bunch.Bunch(d)
    return dct


def dumps(*args, **kwargs):
    """Like json.dumps(), but also serializes Ginga Bunch.Bunch type."""
    d = dict(cls=BunchEncoder)
    d.update(kwargs)
    return json.dumps(*args, **d)

def loads(*args, **kwargs):
    """Like for json.loads(), but also deserializes Ginga Bunch.Bunch type."""
    d = dict(object_hook=as_bunch)
    d.update(kwargs)
    return json.loads(*args, **d)
