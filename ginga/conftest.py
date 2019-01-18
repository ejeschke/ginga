# This contains imports plugins that configure pytest for Ginga tests.
# By importing them here in conftest.py they are discoverable by pytest
# no matter how it is invoked within the source tree.

from astropy.tests.helper import enable_deprecations_as_exceptions
from astropy.tests.plugins.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS

## Uncomment the following line to treat all DeprecationWarnings as
## exceptions
enable_deprecations_as_exceptions()

## Uncomment and customize the following lines to add/remove entries from
## the list of packages for which version numbers are displayed when running
## the tests. Making it pass for KeyError is essential in some cases when
## the package uses other Astropy affiliated packages.
try:
    PYTEST_HEADER_MODULES['Astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'
    del PYTEST_HEADER_MODULES['h5py']
except KeyError:
    pass

## Uncomment the following lines to display the version number of the
## package rather than the version number of Astropy in the top line when
## running the tests.
import os

## This is to figure out the affiliated package version, rather than
## using Astropy's
from . import version

try:
    packagename = os.path.basename(os.path.dirname(__file__))
    TESTED_VERSIONS[packagename] = version.version
except KeyError:
    pass
