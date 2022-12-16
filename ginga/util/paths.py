#
# paths.py -- path information
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os

import ginga.icons
from ginga import __file__ as _pkgf

ginga_pkgdir = os.path.dirname(_pkgf)

ginga_home = None
# this is supposedly the canonical method to get home directory
# across platforms
home = os.path.expanduser('~')

# path to our icons
icondir = os.path.split(ginga.icons.__file__)[0]


if 'GINGA_HOME' in os.environ:
    # User override
    ginga_home = os.environ['GINGA_HOME']

else:
    ginga_home = os.path.join(home, '.ginga')


# END
