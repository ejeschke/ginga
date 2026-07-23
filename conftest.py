# Licensed under a 3-clause BSD style license - see LICENSE.txt
import platform
from importlib.metadata import version, PackageNotFoundError

try:
    from ginga import __version__ as ginga_version
except ImportError:
    ginga_version = 'unknown'

# Packages whose versions are shown in the pytest session-header banner
# (previously provided by pytest-astropy-header).  Maps the display name to
# the installed-distribution (metadata) name.  Versions are read from the
# distribution metadata rather than by importing the packages, so building
# the banner has no import-time side effects -- notably, it does not import
# photutils, whose older releases emit a deprecation warning at import time
# (via astropy's removed TestRunner) that ``filterwarnings = error`` would
# otherwise turn into a session-start crash.
HEADER_MODULES = [
    ('Numpy', 'numpy'),
    ('Scipy', 'scipy'),
    ('Matplotlib', 'matplotlib'),
    ('Astropy', 'astropy'),
    ('photutils', 'photutils'),
    ('Pillow', 'pillow'),
    ('QtPy', 'qtpy'),
]


def pytest_report_header(config):
    versions = []
    for display, dist in HEADER_MODULES:
        try:
            versions.append('{} {}'.format(display, version(dist)))
        except PackageNotFoundError:
            versions.append('{} not installed'.format(display))

    return [
        'ginga version {}'.format(ginga_version),
        'Python {} on {}'.format(platform.python_version(),
                                 platform.platform()),
        'Package versions: {}'.format(', '.join(versions)),
    ]
