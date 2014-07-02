#
# path.py -- path information
# 
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os

home = None
ginga_home = None

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
