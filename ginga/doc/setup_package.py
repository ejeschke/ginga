# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import


# not yet working...
#import os
#srcdir = os.path.dirname(__file__)
#def get_docs():
#    docdir = os.path.join(srcdir, 'doc')
#    res = []
#    # ['../../doc/Makefile', 'doc/conf.py', 'doc/*.rst',
#    #                              'doc/manual/*.rst', 'doc/figures/*.png']
#    return res
#get_package_data():
#    return {'ginga.doc': get_docs()}


def get_package_data():
    return {'ginga.doc': ['manual/*.html']}
