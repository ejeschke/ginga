#
# VecHelp.py -- help classes for vector drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga.fonts import font_asst

IMAGE = 0
LINE = 1
CIRCLE = 2
BEZIER = 3
ELLIPSE_BEZIER = 4
POLYGON = 5
PATH = 6
TEXT = 7


class Pen(object):
    def __init__(self, color='black', linewidth=1, linestyle='solid',
                 alpha=1.0):
        self.color = color
        self.linewidth = linewidth
        self.linestyle = linestyle
        self.alpha = alpha


class Brush(object):
    def __init__(self, color='black', fill=False, alpha=1.0):
        self.color = color
        self.fill = fill
        self.alpha = alpha


class Font(object):
    def __init__(self, fontname='Roboto', fontsize=12.0, color='black',
                 linewidth=1, alpha=1.0):
        fontname = font_asst.resolve_alias(fontname, fontname)
        self.fontname = fontname
        self.fontsize = float(fontsize)
        self.color = color
        self.linewidth = linewidth
        self.alpha = alpha


#END
