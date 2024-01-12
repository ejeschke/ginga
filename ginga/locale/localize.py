#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gettext
import os

localedir = os.path.abspath(os.path.dirname(__file__))
translate = gettext.translation('ginga', localedir, fallback=True)

# for testing
#_ = lambda x: x

_ = translate.gettext
_tr = translate.gettext
