try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    TESTED_VERSIONS = {}
    PYTEST_HEADER_MODULES = {}

try:
    from ginga import __version__ as version
except ImportError:
    version = 'unknown'

# Uncomment and customize the following lines to add/remove entries
# from the list of packages for which version numbers are displayed
# when running the tests.
PYTEST_HEADER_MODULES['Astropy'] = 'astropy'
PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'

TESTED_VERSIONS['ginga'] = version
