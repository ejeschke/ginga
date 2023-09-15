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
PYTEST_HEADER_MODULES['photutils'] = 'photutils'
PYTEST_HEADER_MODULES['Pillow'] = 'PIL'
PYTEST_HEADER_MODULES['QtPy'] = 'qtpy'
PYTEST_HEADER_MODULES.pop('h5py', None)
PYTEST_HEADER_MODULES.pop('Pandas', None)

TESTED_VERSIONS['ginga'] = version
