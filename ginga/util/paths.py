#
# paths.py -- path information
# 
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import ginga.icons

home = None
ginga_home = None

# path to our icons
icondir = os.path.split(ginga.icons.__file__)[0]


if 'GINGA_HOME' in os.environ:
    # User override
    ginga_home = os.environ['GINGA_HOME']

elif 'HOME' in os.environ:
    # Posix/Linux/Mac
    home = os.environ['HOME']
    ginga_home = os.path.join(home, '.ginga')
    
elif ('HOMEDRIVE' in os.environ) and ('HOMEPATH' in os.environ):
    # MS 
    home = os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'])
    ginga_home = os.path.join(home, '.ginga')

else:
    raise Exception("Can't find home directory, please set HOME or GINGA_HOME environment variables")

#END
