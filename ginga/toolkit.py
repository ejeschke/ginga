#
# toolkit.py -- module for customizing Ginga GUI toolkit version
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

toolkit = 'choose'
family = None

class ToolKitError(Exception):
    pass

def use(name):
    """
    Set the name of the GUI toolkit we should use.
    """
    global toolkit, family

    name = name.lower()

    if name.startswith('choose'):
        pass

    elif name.startswith('qt') or name.startswith('pyside'):
        family = 'qt'
        if name == 'qt':
            name = 'qt4'
        assert name in ('qt4', 'pyside', 'qt5'), \
               ToolKitError("ToolKit '%s' not supported!" % (name))

    elif name.startswith('gtk'):
        family = 'gtk'
        if name == 'gtk':
            name = 'gtk2'
        assert name in ('gtk2', ), \
               ToolKitError("ToolKit '%s' not supported!" % (name))

    elif name.startswith('tk'):
        family = 'tk'
        assert name in ('tk', ), \
               ToolKitError("ToolKit '%s' not supported!" % (name))

    else:
        ToolKitError("ToolKit '%s' not supported!" % (name))

    toolkit = name

def get_toolkit():
    return toolkit

def get_family():
    return family

def get_rv_toolkits():
    """Returns a list of reference viewer supported toolkits."""
    return ['qt4', 'qt5', 'pyside', 'gtk']

#END
