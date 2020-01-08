# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""See LONG_DESC.txt"""

# Set up the version
from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = 'unknown'

try:
    # As long as we're using setuptools/distribute, we need to do this the
    # setuptools way or else pkg_resources will throw up unnecessary and
    # annoying warnings (even though the namespace mechanism will still
    # otherwise work without it).
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    pass

__path__ = __import__('pkgutil').extend_path(__path__, __name__)  # noqa

# END
